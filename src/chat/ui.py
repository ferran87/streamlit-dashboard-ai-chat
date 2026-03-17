"""Chat UI helpers for the AI Chat page."""

from __future__ import annotations

import streamlit as st

SUGGESTED_QUESTIONS = [
    "What is the total revenue?",
    "Which product generated the most revenue?",
    "How does revenue compare across regions?",
    "What is the average order value?",
    "Show me the top 5 products by quantity sold.",
]


def init_chat_state() -> None:
    """Initialise session-state keys for the chat."""
    if "messages" not in st.session_state:
        st.session_state.messages = []


def render_chat_history() -> None:
    """Display all past messages."""
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def render_suggested_questions() -> str | None:
    """Show clickable suggested questions; return the chosen one or None."""
    if st.session_state.messages:
        return None
    st.markdown("**Suggested questions:**")
    cols = st.columns(len(SUGGESTED_QUESTIONS))
    for col, q in zip(cols, SUGGESTED_QUESTIONS):
        if col.button(q, key=f"sq_{q}"):
            return q
    return None
