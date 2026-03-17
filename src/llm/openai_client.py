"""Thin wrapper around the OpenAI Chat Completions API."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

SYSTEM_PROMPT = (
    "You are a data analyst. Answer only from the provided data context and "
    "pre-computed metrics. Do not invent numbers. If the context does not "
    "contain enough information, say: 'I don't have that information in the data.' "
    "Be concise. When citing a number, reference the metric id in brackets, "
    "e.g. [total_revenue]."
)


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("OPENAI_API_KEY")
        except Exception:
            pass
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY not found. Set it in .env or Streamlit secrets."
        )
    return OpenAI(api_key=api_key)


def complete(
    context: str,
    user_message: str,
    *,
    model: str = "gpt-4o",
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> str:
    """Send context + user question to the LLM and return the response text."""
    client = _get_client()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{context}\n\n---\nUser question: {user_message}"},
    ]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content
