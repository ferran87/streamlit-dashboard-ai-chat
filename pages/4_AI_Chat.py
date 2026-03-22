"""
pages/4_AI_Chat.py
------------------
AI Analytics Assistant powered by the multi-agent architecture.

Flow:
  User types question
  → Orchestrator decomposes the question
  → Analytics Agent fetches exact numbers via tools
  → Insights Agent interprets results vs benchmarks
  → Orchestrator synthesises final answer
  → Response displayed with tool call trace in st.status()

The message history is preserved in st.session_state across turns.
"""

import streamlit as st
from data.loader import load_all
from src.agents.orchestrator import run_turn

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.title("🤖 AI Analytics Assistant")
st.caption(
    "Ask anything about your funnel metrics. "
    "The AI uses **live data only** — no hallucinations."
)

# ---------------------------------------------------------------------------
# Load data (cached)
# ---------------------------------------------------------------------------
dfs = load_all()

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------------------------------------------------------------------
# Suggested starter questions
# ---------------------------------------------------------------------------
if not st.session_state.messages:
    st.markdown("**Try asking:**")
    cols = st.columns(3)
    starters = [
        "What is our overall conversion rate?",
        "Which channel drives the most activations?",
        "Is our discount strategy working?",
        "What's the worst-performing funnel step?",
        "How does mobile CVR compare to desktop?",
        "Which meal type is most popular at activation?",
    ]
    for i, q in enumerate(starters):
        if cols[i % 3].button(q, key=f"starter_{i}"):
            st.session_state.messages.append({"role": "user", "content": q})
            st.rerun()

# ---------------------------------------------------------------------------
# Render message history
# ---------------------------------------------------------------------------
for msg in st.session_state.messages:
    role = msg["role"]
    # Handle both plain string content and list-of-blocks content
    if isinstance(msg["content"], str):
        content_text = msg["content"]
    elif isinstance(msg["content"], list):
        content_text = " ".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in msg["content"]
            if not isinstance(block, dict) or block.get("type") == "text"
        )
    else:
        content_text = str(msg["content"])

    if role in ("user", "assistant") and content_text.strip():
        with st.chat_message(role):
            st.markdown(content_text)

# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------
if prompt := st.chat_input("Ask about CVR, funnel steps, discounts, meal types…"):
    # Show user message immediately
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Run agent turn
    with st.chat_message("assistant"):
        with st.status("Thinking…", expanded=True) as status:
            try:
                response_text, updated_messages = run_turn(
                    messages=st.session_state.messages,
                    datasets=dfs,
                    status_container=status,
                )
                status.update(label="Done", state="complete", expanded=False)
            except Exception as e:
                status.update(label="Error", state="error", expanded=True)
                response_text = f"⚠️ An error occurred: {e}"
                updated_messages = st.session_state.messages

        st.markdown(response_text)

    # Persist updated message history (includes all tool messages from agent turn)
    st.session_state.messages = updated_messages
    # Append the final assistant response
    st.session_state.messages.append({"role": "assistant", "content": response_text})

# ---------------------------------------------------------------------------
# Sidebar: session controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Session")
    if st.button("🗑️ Clear conversation"):
        st.session_state.messages = []
        st.rerun()
    st.caption(f"{len(st.session_state.messages)} messages in history")
