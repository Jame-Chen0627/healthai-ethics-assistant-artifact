"""LLM-backed handlers for the three Ethics Assistant modes.

Reuses the existing Gemini wrapper (`_call_gemini`, `_safe_json_loads`) from
`llm_service.py`. Each function:
  1. pulls grounding from the static knowledge base (frameworks / findings),
  2. injects it into a system prompt with a strict JSON output schema,
  3. parses the response into a Python dict that mirrors the Pydantic schemas.

Stakeholders: 'HCP' (healthcare professional), 'SEng' (software engineer),
'HCR' (healthcare researcher).
"""

import json
import re
from typing import Optional

from . import llm_service
from ..data import kb


_STAKEHOLDER_LABELS = {
    "HCP": "Healthcare Professional (e.g. clinician, nurse, radiologist)",
    "SEng": "Software Engineer building healthcare AI systems",
    "HCR": "Healthcare Researcher conducting AI-related health research",
}


def _stakeholder_label(stakeholder: str, custom_persona: Optional[str] = None) -> str:
    if custom_persona:
        text = custom_persona.strip()
        if text:
            # Keep prompts compact; cap very long persona blobs.
            return text if len(text) <= 800 else text[:800] + "…"
    return _STAKEHOLDER_LABELS.get(stakeholder, stakeholder)


def _format_frameworks_for_prompt(items: list[dict]) -> str:
    lines = []
    for f in items:
        lines.append(
            f"- id={f['id']} | {f['framework']} {f['article']} — {f['title']}: {f['summary']}"
        )
    return "\n".join(lines) if lines else "(none)"


def _format_findings_for_prompt(items: list[dict]) -> str:
    lines = []
    for x in items:
        lines.append(
            f"- id={x['id']} | source={x['source']} | stakeholder={x['stakeholder']} | "
            f"dimension={x['dimension']} | quote=\"{x['quote']}\" | implication=\"{x['implication']}\""
        )
    return "\n".join(lines) if lines else "(none)"


# Hard cap on injected RAG context to keep prompts reasonable.
_MAX_RAG_CHARS = 12000


def _format_topic_context(topic: Optional[str], topic_prompt: Optional[str]) -> Optional[str]:
    """Render a topic label + optional user-supplied description into a context block.

    Returns None when the topic is empty or the default healthcare topic, so
    behaviour for the built-in 'HealthAI Ethics' topic is unchanged.
    """
    if not topic:
        return None
    label = topic.strip()
    if not label or label.lower() in ("healthai ethics", "healthai-ethics"):
        return None
    parts = [f"CHAT TOPIC: {label}"]
    if topic_prompt and topic_prompt.strip():
        body = topic_prompt.strip()
        if len(body) > 2000:
            body = body[:2000] + "\u2026[truncated]"
        parts.append(f"Topic description from the user:\n{body}")
    parts.append(
        "Treat this topic as the domain for the response. The Create / Validate / "
        "Compare output schemas remain the same; reinterpret frameworks, checks, "
        "and practitioner findings for this domain when needed."
    )
    return "\n\n".join(parts)


def _is_default_healthai_topic(topic: Optional[str]) -> bool:
    if not topic:
        return True
    label = topic.strip().lower()
    return label in ("healthai ethics", "healthai-ethics")


def _topic_label(topic: Optional[str]) -> str:
    return (topic or "HealthAI Ethics").strip() or "HealthAI Ethics"


def _slug(text: str, fallback: str = "topic-guidance") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or fallback


def _topic_guidance_block(topic: Optional[str], topic_prompt: Optional[str]) -> str:
    label = _topic_label(topic)
    if _is_default_healthai_topic(topic):
        return "CHAT TOPIC: HealthAI Ethics (built-in healthcare AI ethics knowledge base)."
    lines = [f"CHAT TOPIC: {label}"]
    if topic_prompt and topic_prompt.strip():
        lines.append(f"Topic description / guidance:\n{topic_prompt.strip()[:2000]}")
    lines.append(
        "Use this topic as the domain authority. Do not assume the built-in "
        "HealthAI Ethics frameworks apply unless the topic description or user "
        "reference documents explicitly mention them."
    )
    return "\n\n".join(lines)


def _format_rag_context(rag_docs: Optional[list[dict]]) -> Optional[str]:
    """Render a list of {name, content} docs into a single context string."""
    if not rag_docs:
        return None
    blocks: list[str] = []
    used = 0
    for d in rag_docs:
        name = (d.get("name") or "untitled").strip()
        content = (d.get("content") or "").strip()
        if not content:
            continue
        remaining = _MAX_RAG_CHARS - used
        if remaining <= 0:
            blocks.append(f"[Additional documents truncated to fit context budget.]")
            break
        if len(content) > remaining:
            content = content[:remaining] + "\n\u2026[truncated]"
        blocks.append(f"--- DOC: {name} ---\n{content}")
        used += len(content)
    if not blocks:
        return None
    return "USER REFERENCE DOCS (treat as authoritative for this request):\n\n" + "\n\n".join(blocks)


def _format_suppressed_requirements(items: Optional[list[dict]]) -> Optional[str]:
    """Render per-session suppressed requirements into a prompt constraint."""
    if not items:
        return None
    lines: list[str] = []
    for idx, item in enumerate(items[:20], start=1):
        text = (item.get("requirement_text") or item.get("requirement") or "").strip()
        if not text:
            continue
        title = (item.get("title") or "").strip()
        prefix = f"{idx}. "
        if title:
            prefix += f"{title}: "
        lines.append(prefix + text[:900])
    if not lines:
        return None
    return (
        "SESSION REQUIREMENT PREFERENCES:\n"
        "The user cleared the following requirements from this chat. In Create mode, "
        "do not generate requirements that are substantially similar; propose a meaningfully different angle instead.\n"
        + "\n".join(lines)
    )


def _apply_overrides(
    defaults: dict, params_override: Optional[dict]
) -> tuple[float, int, Optional[str]]:
    """Merge per-call defaults with optional Developer-Mode overrides."""
    temp = defaults["temperature"]
    max_tok = defaults["max_tokens"]
    model = None
    if params_override:
        if params_override.get("temperature") is not None:
            temp = float(params_override["temperature"])
        if params_override.get("max_tokens") is not None:
            max_tok = int(params_override["max_tokens"])
        if params_override.get("model"):
            model = str(params_override["model"]).strip()
    return temp, max_tok, model


# ── Mode 1: Create Requirements ──────────────────────────────────


async def create_requirements(
    stakeholder: str,
    system_context: str,
    concern_text: str,
    dimensions: Optional[list[str]] = None,
    custom_persona: Optional[str] = None,
    rag_context: Optional[str] = None,
    topic: Optional[str] = None,
    topic_prompt: Optional[str] = None,
    params_override: Optional[dict] = None,
    debug_sink: Optional[list] = None,
) -> dict:
    """Generate ethical concerns + draft requirements grounded in known frameworks."""
    candidate_frameworks = kb.find_frameworks(dimensions=dimensions) if dimensions else kb.get_frameworks()

    persona_label = _stakeholder_label(stakeholder, custom_persona)
    default_topic = _is_default_healthai_topic(topic)
    if default_topic:
        grounding_rules = f"""AVAILABLE FRAMEWORKS:
{_format_frameworks_for_prompt(candidate_frameworks)}

Rules:
- Generate 1 to 3 concerns relevant to the stakeholder, system context, and the concern text.
- Each concern's `guideline_refs` MUST cite ids from the AVAILABLE FRAMEWORKS list. Do not invent articles.
- Tailor requirement wording to a {persona_label} perspective."""
    else:
        grounding_rules = f"""TOPIC GUIDANCE:
{_topic_guidance_block(topic, topic_prompt)}

Rules:
- Generate 1 to 3 concerns relevant to the stakeholder, system context, concern text, and chat topic.
- Use the closest `dimension` value from the output schema, even when the custom topic uses different terminology.
- For `guideline_refs`, cite named standards, frameworks, heuristics, or source documents from the topic description or USER REFERENCE DOCS when available.
- For custom-topic citations, use a stable lowercase id such as `{_slug(_topic_label(topic))}-guidance-1`; leave `guideline_refs` empty if no citation source is available.
- Tailor requirement wording to a {persona_label} perspective."""

    default_identity_note = (
        " For the built-in HealthAI Ethics topic, you are acting as an AI Ethics Assistant."
        if default_topic
        else ""
    )
    system_prompt = f"""You are HealthAI Ethics Assistant, a requirements-engineering assistant.{default_identity_note}
You help a {persona_label} translate concerns into implementable software requirements.

You MUST respond with valid JSON only — no markdown, no commentary.
Output schema:
{{
  "concerns": [
    {{
      "dimension": "privacy" | "safety" | "bias" | "transparency" | "accountability",
      "title": "<short concern title>",
      "description": "<2-4 sentence concrete description tied to the system context>",
      "requirement": "<one or two sentence implementable requirement statement>",
      "guideline_refs": [
        {{"id": "<framework id from the list below>", "framework": "<name>", "article": "<article id>"}}
      ]
    }}
  ]
}}

{grounding_rules}
"""

    user_content = (
        f"System context:\n{system_context}\n\n"
        f"Concern from the developer:\n{concern_text}"
    )
    if rag_context:
        user_content = f"{rag_context}\n\n{user_content}"

    temp, max_tok, model = _apply_overrides(
        {"temperature": 0.4, "max_tokens": 4096}, params_override
    )
    raw = await llm_service._call_gemini(
        system_prompt, user_content, temperature=temp, max_tokens=max_tok,
        model=model, debug_sink=debug_sink,
    )
    parsed = llm_service._safe_json_loads(raw, "create_requirements")

    # Enrich guideline_refs with title/summary from the KB so the UI can render badges
    fw_by_id = {f["id"]: f for f in kb.get_frameworks()}
    for concern in parsed.get("concerns", []):
        enriched_refs = []
        for ref in concern.get("guideline_refs", []) or []:
            ref_id = ref.get("id")
            kb_entry = fw_by_id.get(ref_id)
            if kb_entry:
                enriched_refs.append(
                    {
                        "id": kb_entry["id"],
                        "framework": kb_entry["framework"],
                        "article": kb_entry["article"],
                        "title": kb_entry["title"],
                    }
                )
            elif ref.get("framework") and ref.get("article"):
                enriched_refs.append(
                    {
                        "id": ref_id or "",
                        "framework": ref["framework"],
                        "article": ref["article"],
                        "title": ref.get("title", ""),
                    }
                )
        concern["guideline_refs"] = enriched_refs
    return parsed


# ── Mode 2: Validate Requirements ────────────────────────────────


async def validate_requirements(
    stakeholder: str,
    requirement_text: str,
    framework_names: Optional[list[str]] = None,
    custom_persona: Optional[str] = None,
    rag_context: Optional[str] = None,
    topic: Optional[str] = None,
    topic_prompt: Optional[str] = None,
    params_override: Optional[dict] = None,
    debug_sink: Optional[list] = None,
) -> dict:
    """Validate a requirement against selected frameworks; flag missing controls."""
    default_topic = _is_default_healthai_topic(topic)
    target_frameworks = []
    if default_topic:
        target_frameworks = (
            kb.find_frameworks(framework_names=framework_names)
            if framework_names
            else kb.get_frameworks()
        )

    if default_topic:
        target_guidance = f"""TARGET FRAMEWORKS:
{_format_frameworks_for_prompt(target_frameworks)}

Rules:
- Evaluate ONLY the articles in the TARGET FRAMEWORKS list below.
- Use status "not_applicable" only if an article truly does not apply to this requirement.
- Each `id`/`framework`/`article` combination MUST come from the list. Do not invent articles."""
        assistant_identity = "You are an AI Ethics Assistant validating a software requirement for healthcare AI."
    else:
        topic_slug = _slug(_topic_label(topic))
        target_guidance = f"""TARGET GUIDANCE:
{_topic_guidance_block(topic, topic_prompt)}

Rules:
- Evaluate the requirement against the custom topic description and any USER REFERENCE DOCS supplied in the user content.
- Produce 3 to 6 topic-specific checks that a practitioner in this domain would expect.
- Do NOT cite EU AI Act, NIST AI RMF, or healthcare AI articles unless they are explicitly mentioned in the topic description or USER REFERENCE DOCS.
- If the requirement appears to come from a different domain than the chat topic, extract the underlying requirements pattern (for example access control, consent, audit logging, data retention, safety, accountability) and validate how that pattern should be expressed for the current topic.
- Do NOT return every check as "not_applicable" solely because the nouns in the requirement belong to another domain. Prefer "missing" with a suggested topic-specific rewrite.
- Use status "not_applicable" only for a single check whose control concept truly has no meaningful analogue in the current topic.
- For `id`, use stable lowercase ids such as `{topic_slug}-check-1`, `{topic_slug}-check-2`.
- For `framework`, use the named framework/source when one is provided (for example OWASP ASVS, ISO/IEC 27001, WCAG, Nielsen heuristics); otherwise use the chat topic label.
- For `article`, use the specific clause/control/principle when known; otherwise use "Guidance".
- For `title`, use a short check title."""
        assistant_identity = "You are HealthAI Ethics Assistant, a requirements-engineering assistant validating a software requirement."

    system_prompt = f"""{assistant_identity}
The user is a {_stakeholder_label(stakeholder, custom_persona)}.

You MUST respond with valid JSON only — no markdown, no commentary.
Output schema:
{{
  "checks": [
    {{
      "id": "<framework id from the list below>",
      "framework": "<name>",
      "article": "<article id>",
      "title": "<article title>",
      "status": "valid" | "missing" | "not_applicable",
      "gap": "<what is missing or insufficient; empty string if valid/not_applicable>",
      "suggested_addition": "<concrete addition to the requirement; empty string if status=valid>"
    }}
  ],
  "summary": "<one-sentence verdict, e.g. 'Requirement needs 2 additions for full compliance'>"
}}

{target_guidance}
"""

    user_content = f"Requirement to validate:\n{requirement_text}"
    if rag_context:
        user_content = f"{rag_context}\n\n{user_content}"

    temp, max_tok, model = _apply_overrides(
        {"temperature": 0.2, "max_tokens": 4096}, params_override
    )
    raw = await llm_service._call_gemini(
        system_prompt, user_content, temperature=temp, max_tokens=max_tok,
        model=model, debug_sink=debug_sink,
    )
    parsed = llm_service._safe_json_loads(raw, "validate_requirements")

    # Backfill title from KB
    fw_by_id = {f["id"]: f for f in kb.get_frameworks()}
    for check in parsed.get("checks", []) or []:
        kb_entry = fw_by_id.get(check.get("id"))
        if kb_entry:
            check.setdefault("title", kb_entry["title"])
            check["framework"] = kb_entry["framework"]
            check["article"] = kb_entry["article"]
    return parsed


# ── Mode 3: Compare with Real-World Scenarios ────────────────────


async def compare_scenarios(
    stakeholder: str,
    requirement_text: str,
    dimension: Optional[str] = None,
    custom_persona: Optional[str] = None,
    rag_context: Optional[str] = None,
    topic: Optional[str] = None,
    topic_prompt: Optional[str] = None,
    params_override: Optional[dict] = None,
    debug_sink: Optional[list] = None,
) -> dict:
    """Surface practitioner / online-discussion insights and propose an enhanced requirement."""
    default_topic = _is_default_healthai_topic(topic)
    candidate_findings = []
    if default_topic:
        candidate_findings = kb.find_findings(dimension=dimension, stakeholder=stakeholder)
        if len(candidate_findings) < 4:
            # Broaden if we have very few stakeholder-specific findings
            candidate_findings = kb.find_findings(dimension=dimension)
        if not candidate_findings:
            candidate_findings = kb.get_findings()

    if default_topic:
        findings_block = f"""AVAILABLE FINDINGS:
{_format_findings_for_prompt(candidate_findings)}

Rules:
- Pick 1 to 3 of the AVAILABLE FINDINGS below that are most relevant to the requirement.
- Use the finding's `id` exactly as listed. Do not invent findings.
- The enhanced requirement must be implementable and one or two sentences."""
        assistant_identity = "You are an AI Ethics Assistant comparing a draft requirement against real-world practitioner experience."
    else:
        topic_slug = _slug(_topic_label(topic))
        findings_block = f"""TOPIC GUIDANCE:
{_topic_guidance_block(topic, topic_prompt)}

Rules:
- Compare the requirement against practical issues, implementation risks, and user/stakeholder concerns for this custom topic.
- Use USER REFERENCE DOCS as the strongest evidence when provided.
- Return 1 to 3 suggestions.
- Use ids such as `{topic_slug}-practice-1`, `{topic_slug}-practice-2`.
- The `source` field must be either "interview" or "reddit"; use "interview" for practitioner or stakeholder experience and "reddit" for public/user-community experience.
- Use the closest `dimension` value from the output schema.
- Keep `quote` short. If no direct quote is available, summarize the practical concern instead of inventing a quotation.
- The enhanced requirement must be implementable and one or two sentences."""
        assistant_identity = "You are HealthAI Ethics Assistant comparing a draft requirement against real-world practice for the chat topic."

    system_prompt = f"""{assistant_identity}
The user is a {_stakeholder_label(stakeholder, custom_persona)}.

You MUST respond with valid JSON only — no markdown, no commentary.
Output schema:
{{
  "original_requirement": "<echo the requirement back>",
  "suggestions": [
    {{
      "id": "<finding id from the list below>",
      "source": "interview" | "reddit",
      "stakeholder": "HCP" | "SEng" | "HCR",
      "dimension": "privacy" | "safety" | "bias" | "transparency" | "accountability",
      "quote": "<short quote from the finding>",
      "recommendation": "<concrete change to the requirement motivated by this finding>"
    }}
  ],
  "enhanced_requirement": "<rewritten requirement that incorporates the most relevant suggestions>"
}}

{findings_block}
"""

    user_content = f"Requirement to compare:\n{requirement_text}"
    if rag_context:
        user_content = f"{rag_context}\n\n{user_content}"

    temp, max_tok, model = _apply_overrides(
        {"temperature": 0.4, "max_tokens": 4096}, params_override
    )
    raw = await llm_service._call_gemini(
        system_prompt, user_content, temperature=temp, max_tokens=max_tok,
        model=model, debug_sink=debug_sink,
    )
    parsed = llm_service._safe_json_loads(raw, "compare_scenarios")

    if default_topic:
        finding_by_id = {x["id"]: x for x in kb.get_findings()}
        for sug in parsed.get("suggestions", []) or []:
            kb_entry = finding_by_id.get(sug.get("id"))
            if kb_entry:
                sug["source"] = kb_entry["source"]
                sug["stakeholder"] = kb_entry["stakeholder"]
                sug["dimension"] = kb_entry["dimension"]
                # Prefer the canonical quote from the KB
                sug["quote"] = kb_entry["quote"]
    return parsed


# ── Auto-classification + dispatch ────────────────────────────────


_CLASSIFIER_PROMPT = """You are an intent classifier for HealthAI Ethics Assistant, a requirements-engineering assistant.

The assistant has THREE modes for any chat topic:
  - "create"   : the user describes an ethical concern or system context and wants
                 the assistant to GENERATE concerns + draft requirements.
                 Triggers: "help me draft", "what requirements", "I'm worried about...",
                 "we are building X", general open-ended concerns without a concrete
                 requirement statement.
  - "validate" : the user provides an EXISTING requirement statement and wants it
                 checked against the current topic's guidelines, standards, heuristics,
                 or reference documents.
                 Triggers: "is this requirement compliant", "validate", "check this:",
                 a sentence that already reads like a software requirement.
  - "compare"  : the user has a requirement and wants real-world practitioner
                 perspective (interview / Reddit findings) to enhance it.
                 Triggers: "what would clinicians say", "real-world", "improve this
                 requirement", "compare with practice".

Respond with JSON ONLY:
{
  "mode": "create" | "validate" | "compare",
  "assistant_text": "<one short sentence telling the user what you're about to do>",
  "concern_text":      "<for create:   the ethical concern, possibly cleaned up>",
  "system_context":    "<for create:   the AI system being built; copy from the prompt or '' if absent>",
  "requirement_text":  "<for validate/compare: the requirement statement>",
  "dimension":         "privacy" | "safety" | "bias" | "transparency" | "accountability" | null
}

Rules:
- Choose exactly ONE mode.
- Fill ONLY the fields relevant to the chosen mode; leave others as empty strings or null.
- Never invent a requirement that the user didn't supply.
"""


async def classify_intent(
    prompt: str,
    system_context_hint: str | None = None,
    topic: str | None = None,
    topic_prompt: str | None = None,
    params_override: Optional[dict] = None,
    debug_sink: Optional[list] = None,
) -> dict:
    """Pick mode + extract structured fields from a free-form prompt."""
    user_content = f"User prompt:\n{prompt}"
    if topic or topic_prompt:
        user_content += f"\n\n{_topic_guidance_block(topic, topic_prompt)}"
    if system_context_hint:
        user_content += f"\n\nSession context hint:\n{system_context_hint}"

    # Note: classifier intentionally ignores temperature override (must stay
    # near-deterministic) but still honours model + max_tokens.
    _, max_tok, model = _apply_overrides(
        {"temperature": 0.1, "max_tokens": 1200}, params_override
    )
    raw = await llm_service._call_gemini(
        _CLASSIFIER_PROMPT, user_content, temperature=0.1, max_tokens=max_tok,
        model=model, debug_sink=debug_sink,
    )
    parsed = llm_service._safe_json_loads(raw, "classify_intent")
    mode = parsed.get("mode")
    if mode not in ("create", "validate", "compare"):
        # Fallback heuristic
        mode = "create"
        parsed["mode"] = mode
    return parsed


async def chat(
    stakeholder: str,
    prompt: str,
    system_context_hint: str | None = None,
    custom_persona: str | None = None,
    rag_docs: Optional[list[dict]] = None,
    suppressed_requirements: Optional[list[dict]] = None,
    topic: Optional[str] = None,
    topic_prompt: Optional[str] = None,
    params_override: Optional[dict] = None,
    debug_sink: Optional[list] = None,
) -> dict:
    """Auto-classify the user's free-form prompt and dispatch to the right mode.

    Returns a dict ready to feed into `EthicsChatResponse`.
    """
    rag_context = _format_rag_context(rag_docs)
    suppression_block = _format_suppressed_requirements(suppressed_requirements)
    if suppression_block:
        rag_context = f"{suppression_block}\n\n{rag_context}" if rag_context else suppression_block
    # If the chat is scoped to a non-default topic, prepend a topic framing
    # block so the LLM knows the domain. We piggy-back on the rag_context
    # channel so all three modes see it without further plumbing.
    topic_block = _format_topic_context(topic, topic_prompt)
    if topic_block:
        rag_context = f"{topic_block}\n\n{rag_context}" if rag_context else topic_block
    intent = await classify_intent(
        prompt,
        system_context_hint=system_context_hint,
        topic=topic,
        topic_prompt=topic_prompt,
        params_override=params_override,
        debug_sink=debug_sink,
    )
    mode = intent["mode"]
    assistant_text = (intent.get("assistant_text") or "").strip()
    out: dict = {"mode": mode, "assistant_text": assistant_text}

    if mode == "create":
        sys_ctx = (intent.get("system_context") or system_context_hint or "").strip()
        concern = (intent.get("concern_text") or prompt).strip()
        if not sys_ctx:
            if _is_default_healthai_topic(topic):
                sys_ctx = "(unspecified — infer a reasonable healthcare AI system from the concern)"
            else:
                sys_ctx = f"(unspecified — infer a reasonable {_topic_label(topic)} system or project from the concern)"
        result = await create_requirements(
            stakeholder=stakeholder,
            system_context=sys_ctx,
            concern_text=concern,
            custom_persona=custom_persona,
            rag_context=rag_context,
            topic=topic,
            topic_prompt=topic_prompt,
            params_override=params_override,
            debug_sink=debug_sink,
        )
        out["create"] = result
    elif mode == "validate":
        req = (intent.get("requirement_text") or prompt).strip()
        result = await validate_requirements(
            stakeholder=stakeholder,
            requirement_text=req,
            custom_persona=custom_persona,
            rag_context=rag_context,
            topic=topic,
            topic_prompt=topic_prompt,
            params_override=params_override,
            debug_sink=debug_sink,
        )
        out["validate"] = result
    else:  # compare
        req = (intent.get("requirement_text") or prompt).strip()
        dim = intent.get("dimension")
        if dim not in kb.ETHICAL_DIMENSIONS:
            dim = None
        result = await compare_scenarios(
            stakeholder=stakeholder,
            requirement_text=req,
            dimension=dim,
            custom_persona=custom_persona,
            rag_context=rag_context,
            topic=topic,
            topic_prompt=topic_prompt,
            params_override=params_override,
            debug_sink=debug_sink,
        )
        out["compare"] = result

    return out
