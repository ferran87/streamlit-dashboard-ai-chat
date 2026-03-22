"""
pages/4_AI_Chat.py
------------------
AI Analytics Assistant powered by the Unified Agent.

Improvements over the original multi-agent version:
  - Single API round-trip (instead of 3-4 sequential hops) → much faster
  - Streaming response: first tokens appear in ~2s
  - Charts rendered inline: agent calls generate_chart → chart appears above text
  - Context cached: recomputed only when dataset changes
  - History pruned: last 20 messages passed to API to prevent context bloat
"""

import streamlit as st
from data.loader import load_all
from src.agents.unified import run_turn, _dispatch_chart_tool

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.title("🤖 AI Analytics Assistant")
st.caption(
    "Ask anything about your funnel metrics. "
    "Powered by a **unified AI agent** with live data tools — no hallucinations."
)

# ---------------------------------------------------------------------------
# Load data (cached — only loaded once per Streamlit process)
# ---------------------------------------------------------------------------
dfs = load_all()

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []


# ---------------------------------------------------------------------------
# History pruning helper
# ---------------------------------------------------------------------------
_MAX_HISTORY = 20

def _prune_history(messages: list[dict]) -> list[dict]:
    """Keep last _MAX_HISTORY messages, starting on a user turn."""
    pruned = messages[-_MAX_HISTORY:] if len(messages) > _MAX_HISTORY else messages
    while pruned and pruned[0].get("role") != "user":
        pruned = pruned[1:]
    return pruned


# ---------------------------------------------------------------------------
# Starter question buttons (shown only on empty history)
# ---------------------------------------------------------------------------
if not st.session_state.messages:
    st.markdown("**Try asking:**")
    starters = [
        "What is our overall conversion rate?",
        "Show me CVR by channel",
        "Which funnel step has the most drop-off?",
        "Is our discount strategy working?",
        "How does mobile CVR compare to desktop?",
        "Show activation trend over time",
    ]
    cols = st.columns(3)
    for i, q in enumerate(starters):
        if cols[i % 3].button(q, key=f"starter_{i}"):
            st.session_state.messages.append({"role": "user", "content": q})
            st.rerun()


# ---------------------------------------------------------------------------
# Render message history (including charts stored per message)
# ---------------------------------------------------------------------------
for msg in st.session_state.messages:
    role = msg.get("role")
    content = msg.get("content", "")
    chart_types = msg.get("chart_types", [])

    # Flatten list-content to text (defensive — messages should be plain strings)
    if isinstance(content, list):
        content = " ".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ).strip()

    if role not in ("user", "assistant") or not content.strip():
        continue

    with st.chat_message(role):
        # Re-render charts for assistant messages that requested them
        if role == "assistant" and chart_types:
            for chart_type in chart_types:
                fig = _dispatch_chart_tool({"chart_type": chart_type}, dfs)
                if fig is not None:
                    st.plotly_chart(fig, use_container_width=True)
        st.markdown(content)


# ---------------------------------------------------------------------------
# Chat input handler
# ---------------------------------------------------------------------------
if prompt := st.chat_input("Ask about CVR, funnel steps, discounts, meal types…"):
    # Append and show user message immediately
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Run unified agent turn
    with st.chat_message("assistant"):
        with st.status("Analysing…", expanded=True) as status:
            try:
                pruned = _prune_history(st.session_state.messages)
                result = run_turn(
                    messages=pruned,
                    datasets=dfs,
                    max_history=_MAX_HISTORY,
                    status_container=status,
                )
                status.update(label="Done ✓", state="complete", expanded=False)
            except Exception as e:
                status.update(label="Error", state="error", expanded=True)
                st.error(f"An error occurred: {e}")
                st.stop()

        # Render charts BEFORE streaming text (charts are ready immediately)
        for fig in result.charts:
            st.plotly_chart(fig, use_container_width=True)

        # Stream the final text response — first tokens appear immediately
        response_text = st.write_stream(result.stream_gen)

    # Persist to session state (store chart_type_ids for history re-render)
    st.session_state.messages.append({
        "role": "assistant",
        "content": response_text,
        "chart_types": result.chart_type_ids,
    })


# ---------------------------------------------------------------------------
# Sidebar: session controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Session")
    if st.button("🗑️ Clear conversation"):
        st.session_state.messages = []
        st.rerun()

    total = len(st.session_state.messages)
    passed = len(_prune_history(st.session_state.messages))
    st.caption(f"{total} messages total · {passed} sent to AI")

    st.divider()
    st.markdown("**How it works**")
    st.markdown(
        "- 📊 Agent fetches exact numbers from live data\n"
        "- ✅ Validates metrics against known benchmarks\n"
        "- 🔍 Generates charts on request\n"
        "- 🚀 Streams response for fast first-token latency"
    )
