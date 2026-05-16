"""Interactive terminal chat for local development.

Run:
    python3 scripts/chat_cli.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.conversation import ChatRequest, ConversationEngine
from src.llm import OpenAICompatibleLLM
from src.storage import MemoryStore
from src.templates import get_active_template


def _print_json(label: str, value: Any) -> None:
    print(f"\n{label}:")
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _parse_set_command(text: str) -> tuple[str, str] | None:
    raw = text.removeprefix("/set").strip()
    if "=" not in raw:
        return None
    key, value = raw.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key or not value:
        return None
    return key, value


async def run_chat(account_id: str) -> None:
    load_dotenv(PROJECT_ROOT / ".env")

    template = get_active_template()
    store = MemoryStore()
    llm = OpenAICompatibleLLM()
    engine = ConversationEngine(template, store, llm)

    profile: dict[str, Any] = {}
    pending_field_key: str | None = None

    print("open-lead-agent terminal chat")
    print(f"template: {template.template.id} - {template.template.name}")
    print(f"llm: {llm.settings.provider} / {llm.settings.model}")
    print(f"accountId: {account_id}")
    print("\nCommands:")
    print("  /exit                 quit")
    print("  /profile              show collected profile")
    print("  /template             show active template summary")
    print("  /set key=value        manually set a profile field")
    print(
        "\nStart chatting. If the agent asks for a field, "
        "your next plain reply is recorded as that field."
    )

    while True:
        user_text = input("\nYou> ").strip()
        if not user_text:
            continue

        if user_text in {"/exit", "/quit", "exit", "quit"}:
            print("bye")
            return

        if user_text == "/profile":
            _print_json("profile", profile)
            continue

        if user_text == "/template":
            _print_json("template", template.public_dict())
            continue

        if user_text.startswith("/set"):
            parsed = _parse_set_command(user_text)
            if parsed is None:
                print("Usage: /set key=value")
                continue
            key, value = parsed
            profile[key] = value
            print(f"set {key}={value}")
            continue

        profile_update: dict[str, Any] = {}
        if pending_field_key:
            profile_update[pending_field_key] = user_text
            profile[pending_field_key] = user_text
            pending_field_key = None

        try:
            response = await engine.chat(
                ChatRequest(
                    question=user_text,
                    accountId=account_id,
                    profile=profile_update,
                )
            )
        except Exception as exc:
            print(f"\nAI call failed: {exc}")
            print("Check LLM_API_KEY / LLM_MODEL / LLM_BASE_URL in .env.")
            continue

        print(f"\nAI> {response.response}")

        if response.collected:
            profile.update(response.collected)
            _print_json("collected", response.collected)

        if response.next_field:
            pending_field_key = response.next_field["key"]
            print(f"\nnext_field: {response.next_field['key']} ({response.next_field['label']})")

        if response.rag_sources:
            _print_json("rag_sources", response.rag_sources)


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive open-lead-agent chat")
    parser.add_argument(
        "--account-id", default="terminal-user", help="Account id for this chat session"
    )
    args = parser.parse_args()
    asyncio.run(run_chat(args.account_id))


if __name__ == "__main__":
    main()
