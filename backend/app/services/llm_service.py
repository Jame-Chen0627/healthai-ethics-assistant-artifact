"""Gemini API wrappers used by the Ethics Assistant.

- `_call_gemini` / `_safe_json_loads`: shared building blocks reused by
  `services/ethics_service.py` for the three structured-output modes.
- `stream_chat_with_gemini`: SSE-style streaming used by the free-form chat
  fallback in `routers/chat.py`.
"""

import asyncio
import json
import random
import re
import httpx
from typing import AsyncIterator
from ..config import settings

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_STREAM_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent"
_RETRYABLE_STATUS_CODES = {429, 500, 503, 504}


def _candidate_models(model: str | None) -> list[str]:
    primary = (model or settings.GEMINI_MODEL).strip()
    models = [primary]
    # Developer-mode explicit model overrides should stay explicit; otherwise
    # use configured fallbacks to ride out transient Gemini capacity issues.
    if model is None:
        models.extend(m.strip() for m in settings.GEMINI_FALLBACK_MODELS if m.strip())
    deduped: list[str] = []
    for candidate in models:
        if candidate and candidate not in deduped:
            deduped.append(candidate)
    return deduped


def _body_preview(resp: httpx.Response) -> str:
    try:
        body = resp.text
    except Exception:
        return ""
    if settings.GEMINI_API_KEY:
        body = body.replace(settings.GEMINI_API_KEY, "[redacted]")
    return body[:500]


def _retry_delay(attempt_idx: int) -> float:
    return min(0.75 * (2 ** attempt_idx), 4.0) + random.uniform(0, 0.35)


async def _call_gemini(
    system_prompt: str,
    user_content: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    model: str | None = None,
    debug_sink: list | None = None,
) -> str:
    """Call Gemini with JSON response mode and return the text payload.

    For Gemini 2.5 "thinking" models, hidden reasoning tokens count against
    `maxOutputTokens` and frequently cause `MAX_TOKENS` truncation on
    structured outputs. We disable the thinking budget here so the entire
    quota is available for the visible JSON response.

    If ``debug_sink`` is provided, a record describing this call is appended:
    ``{prompt, user_content, generationConfig, model, finish_reason,
    usage, raw_response, text}``. The record is also returned via the sink
    when an exception is raised, so the caller can still inspect what was
    sent / received.
    """
    generation_config = {
        "temperature": temperature,
        "maxOutputTokens": max_tokens,
        "responseMimeType": "application/json",
        "thinkingConfig": {"thinkingBudget": 0},
    }
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": user_content}]}],
        "generationConfig": generation_config,
    }

    attempts_per_model = max(1, settings.GEMINI_MAX_RETRIES)
    last_error = "unknown error"
    models = _candidate_models(model)

    async with httpx.AsyncClient(timeout=60) as client:
        for model_idx, actual_model in enumerate(models):
            url = GEMINI_API_URL.format(model=actual_model)
            for attempt_idx in range(attempts_per_model):
                record: dict | None = None
                if debug_sink is not None:
                    record = {
                        "model": actual_model,
                        "attempt": attempt_idx + 1,
                        "system_prompt": system_prompt,
                        "user_content": user_content,
                        "generation_config": generation_config,
                    }
                    debug_sink.append(record)

                try:
                    resp = await client.post(
                        url,
                        params={"key": settings.GEMINI_API_KEY},
                        json=payload,
                    )
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    last_error = f"{type(exc).__name__}: {exc}"
                    if record is not None:
                        record["error"] = last_error
                    should_retry = (
                        attempt_idx < attempts_per_model - 1
                        or model_idx < len(models) - 1
                    )
                    if should_retry:
                        await asyncio.sleep(_retry_delay(attempt_idx))
                        continue
                    raise RuntimeError(
                        f"Gemini API request failed after retries "
                        f"(model={actual_model}): {last_error}"
                    ) from exc

                if resp.status_code in _RETRYABLE_STATUS_CODES:
                    last_error = (
                        f"HTTP {resp.status_code} from Gemini API "
                        f"(model={actual_model}): {_body_preview(resp)}"
                    )
                    if record is not None:
                        record["http_status"] = resp.status_code
                        record["error"] = last_error
                    should_retry = (
                        attempt_idx < attempts_per_model - 1
                        or model_idx < len(models) - 1
                    )
                    if should_retry:
                        await asyncio.sleep(_retry_delay(attempt_idx))
                        continue
                    raise RuntimeError(
                        "Gemini API is temporarily unavailable after retries. "
                        f"Last error: {last_error}"
                    )

                if resp.status_code >= 400:
                    body = _body_preview(resp)
                    if record is not None:
                        record["http_status"] = resp.status_code
                        record["error"] = body
                    raise RuntimeError(
                        f"Gemini API HTTP {resp.status_code} "
                        f"(model={actual_model}): {body}"
                    )

                data = resp.json()
                break
            else:  # pragma: no cover - loop always exits by continue/raise/break
                continue
            break
        else:  # pragma: no cover - defensive guard
            raise RuntimeError(f"Gemini API request failed: {last_error}")

    candidate = (data.get("candidates") or [{}])[0]
    finish_reason = candidate.get("finishReason")
    parts = (candidate.get("content") or {}).get("parts") or []
    text_parts = [p.get("text", "") for p in parts if "text" in p]
    content = "".join(text_parts).strip()

    if record is not None:
        record["finish_reason"] = finish_reason
        record["usage"] = data.get("usageMetadata")
        record["raw_response"] = data
        record["text"] = content

    if not content:
        raise RuntimeError(
            f"Gemini returned no text (finishReason={finish_reason}, model={actual_model}). "
            f"Raw response: {data}"
        )
    if finish_reason == "MAX_TOKENS":
        raise RuntimeError(
            f"Gemini response truncated (MAX_TOKENS, model={actual_model}, "
            f"max_tokens={max_tokens}). Increase max_tokens. Partial text: {content[:200]!r}"
        )

    # Strip markdown code fences if present
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)
    return content


def _safe_json_loads(raw: str, context: str):
    """`json.loads` with a clearer error that includes the raw payload."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Gemini response for {context} was not valid JSON: {e}. Raw text: {raw!r}"
        ) from e


# ── Streaming chat ────────────────────────────────────────────────


DEFAULT_CHAT_SYSTEM_PROMPT = (
    "You are HealthAI Ethics Assistant, a requirements-engineering dialogue assistant. "
    "For the built-in HealthAI Ethics topic, help users reason about ethical "
    "requirements for healthcare AI and reference EU AI Act / NIST AI RMF "
    "articles when relevant. Be concise."
)


def _build_gemini_contents(messages: list[dict]) -> tuple[list[dict], str | None]:
    """Convert {role, content} list to Gemini `contents` format.

    Maps user→user, assistant→model, system→merged extra system instruction.
    """
    contents: list[dict] = []
    system_pieces: list[str] = []
    for m in messages:
        role = m.get("role", "user")
        text = m.get("content", "")
        if not text:
            continue
        if role == "system":
            system_pieces.append(text)
            continue
        gemini_role = "model" if role == "assistant" else "user"
        contents.append({"role": gemini_role, "parts": [{"text": text}]})
    extra_system = "\n\n".join(system_pieces) if system_pieces else None
    return contents, extra_system


async def stream_chat_with_gemini(
    messages: list[dict],
    context_text: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> AsyncIterator[str]:
    """Stream a chat completion from Gemini, yielding text chunks as they arrive."""
    url = GEMINI_STREAM_URL.format(model=settings.GEMINI_MODEL)
    contents, extra_system = _build_gemini_contents(messages)
    if not contents:
        raise ValueError("stream_chat_with_gemini: messages must contain at least one user/assistant message")

    system_parts: list[str] = [DEFAULT_CHAT_SYSTEM_PROMPT]
    if context_text:
        system_parts.append(context_text)
    if extra_system:
        system_parts.append(extra_system)
    system_text = "\n\n".join(system_parts)

    payload = {
        "system_instruction": {"parts": [{"text": system_text}]},
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
        async with client.stream(
            "POST",
            url,
            params={"key": settings.GEMINI_API_KEY, "alt": "sse"},
            json=payload,
        ) as resp:
            if resp.status_code != 200:
                body = (await resp.aread()).decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"Gemini stream HTTP {resp.status_code} (model={settings.GEMINI_MODEL}): {body[:500]}"
                )

            async for raw_line in resp.aiter_lines():
                if not raw_line:
                    continue
                if not raw_line.startswith("data:"):
                    continue
                data_str = raw_line[len("data:"):].strip()
                if not data_str or data_str == "[DONE]":
                    continue
                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                candidates = chunk.get("candidates") or []
                if not candidates:
                    continue
                cand = candidates[0]
                finish_reason = cand.get("finishReason")
                parts = (cand.get("content") or {}).get("parts") or []
                for part in parts:
                    text = part.get("text")
                    if text:
                        yield text
                if finish_reason == "MAX_TOKENS":
                    yield "\n\n[response truncated: MAX_TOKENS]"
                elif finish_reason and finish_reason not in ("STOP", "FINISH_REASON_UNSPECIFIED", None):
                    yield f"\n\n[stream ended: {finish_reason}]"
