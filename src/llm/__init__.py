"""LLM provider dispatch: routes to openai or anthropic based on LLM_PROVIDER env var."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def complete(context: str, user_message: str, **kwargs: object) -> str:
    """Call the configured LLM provider. Set LLM_PROVIDER=openai|anthropic (default: openai)."""
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "anthropic":
        from src.llm.anthropic_client import complete as _complete
    else:
        from src.llm.openai_client import complete as _complete
    return _complete(context, user_message, **kwargs)
