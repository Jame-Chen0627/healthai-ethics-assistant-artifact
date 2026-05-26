"""
Hit a running backend's /chat/stream endpoint and print SSE chunks live.

Usage (backend must be running on :8000):
    python scripts/verify_chat_stream.py
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx


BASE_URL = "http://localhost:8000"


async def main() -> None:
    payload = {
        "messages": [
            {"role": "user", "content": "In one short sentence, what is metamorphic testing?"}
        ],
    }
    print(f"POST {BASE_URL}/chat/stream  (anonymous)")
    print(f"  payload: {payload}\n")

    full_text = []
    done_seen = False
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
        async with client.stream(
            "POST",
            f"{BASE_URL}/chat/stream",
            json=payload,
            headers={"Accept": "text/event-stream"},
        ) as resp:
            if resp.status_code != 200:
                body = (await resp.aread()).decode("utf-8", errors="replace")
                print(f"  ✗ HTTP {resp.status_code}: {body[:500]}")
                sys.exit(1)
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data_str = line[len("data:"):].strip()
                try:
                    evt = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                if evt.get("type") == "chunk":
                    text = evt.get("text", "")
                    full_text.append(text)
                    print(text, end="", flush=True)
                elif evt.get("type") == "done":
                    done_seen = True
                    print(f"\n\n[done event received: {evt}]")
                elif evt.get("type") == "error":
                    print(f"\n\n[error event: {evt}]")
                    sys.exit(1)

    print()
    if not done_seen:
        print("  ✗ stream ended without a 'done' event")
        sys.exit(1)
    if not "".join(full_text).strip():
        print("  ✗ no text received")
        sys.exit(1)
    print(f"  ✓ received {sum(len(t) for t in full_text)} chars across {len(full_text)} chunks")


if __name__ == "__main__":
    asyncio.run(main())
