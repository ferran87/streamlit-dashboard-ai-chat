"""Thin wrapper around the Anthropic Messages API."""

from __future__ import annotations

import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = (
    "You are a data analyst. Answer only from the provided data context and "
    "pre-computed metrics. Do not invent numbers. If the context does not "
    "contain enough information, say: 'I don't have that information in the data.' "
    "Be concise. When citing a number, reference the metric id in brackets, "
    "e.g. [total_revenue]."
)


def _get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("ANTHROPIC_API_KEY")
        except Exception:
            pass
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY not found. Set it in .env or Streamlit secrets."
        )
    return anthropic.Anthropic(api_key=api_key)


def complete(
    context: str,
    user_message: str,
    *,
    model: str = "claude-haiku-4-5-20251001",
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> str:
    """Send context + user question to the LLM and return the response text."""
    client = _get_client()
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"{context}\n\n---\nUser question: {user_message}",
            }
        ],
        temperature=temperature,
    )
    return response.content[0].text
