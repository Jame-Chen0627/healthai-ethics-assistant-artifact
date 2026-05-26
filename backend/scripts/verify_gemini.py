"""
Quick health check for the configured Gemini model.

Usage (from backend/):
    python scripts/verify_gemini.py
"""
import asyncio
import json
import sys
from pathlib import Path

# Allow `from app...` imports when running this script directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from app.config import settings
from app.services.llm_service import _call_gemini, GEMINI_API_URL


LIST_URL = "https://generativelanguage.googleapis.com/v1beta/models"


async def check_key_and_list_models() -> list[str]:
    print("Step 1/3 — Validating API key + listing models ...")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(LIST_URL, params={"key": settings.GEMINI_API_KEY})
    if resp.status_code != 200:
        print(f"  ✗ HTTP {resp.status_code}: {resp.text[:300]}")
        sys.exit(1)
    models = [m["name"].removeprefix("models/") for m in resp.json().get("models", [])]
    print(f"  ✓ Key works. {len(models)} models visible.")
    return models


async def check_model_available(models: list[str]) -> None:
    print(f"Step 2/3 — Checking model '{settings.GEMINI_MODEL}' is in the list ...")
    if settings.GEMINI_MODEL in models:
        print(f"  ✓ '{settings.GEMINI_MODEL}' is available.")
        return
    print(f"  ✗ '{settings.GEMINI_MODEL}' NOT found.")
    suggestions = [m for m in models if "gemini-3" in m or "gemini-2.5" in m]
    if suggestions:
        print("  Suggestions (set GEMINI_MODEL to one of):")
        for m in sorted(suggestions):
            print(f"    - {m}")
    sys.exit(1)


async def check_generate_content() -> None:
    print(f"Step 3/3 — Calling generateContent with JSON response ...")
    try:
        raw = await _call_gemini(
            system_prompt="You are a JSON generator. Reply ONLY with valid JSON.",
            user_content='Return this exact JSON object: {"status":"ok","model":"' + settings.GEMINI_MODEL + '"}',
            temperature=0.0,
            max_tokens=2000,
        )
    except httpx.HTTPStatusError as e:
        print(f"  ✗ HTTP {e.response.status_code}: {e.response.text[:400]}")
        sys.exit(1)
    except Exception as e:
        print(f"  ✗ Unexpected error: {type(e).__name__}: {e}")
        sys.exit(1)

    print(f"  Raw response: {raw}")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  ✗ Response is not valid JSON: {e}")
        sys.exit(1)
    print(f"  ✓ Parsed JSON OK: {parsed}")


async def main() -> None:
    print(f"Endpoint: {GEMINI_API_URL.format(model=settings.GEMINI_MODEL)}")
    print(f"Key:      {settings.GEMINI_API_KEY[:8]}...{settings.GEMINI_API_KEY[-4:]}")
    print()
    models = await check_key_and_list_models()
    await check_model_available(models)
    await check_generate_content()
    print("\nAll checks passed. Backend should be able to talk to Gemini.")


if __name__ == "__main__":
    asyncio.run(main())
