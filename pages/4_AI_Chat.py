"""AI Analytics Assistant — unified agent with streaming and inline charts."""

import json
import re
import streamlit as st
from data.loader import load_all
from src.agents.unified import run_turn, dispatch_chart_tool

_MAX_HISTORY = 20

_LIMITATION_PATTERNS = re.compile(
    r"(?i)(can'?t create|can'?t generate|can'?t produce|can'?t show|can'?t plot|"
    r"can'?t build|not available|not possible|unfortunately|unable to|"
    r"none of the available|no available (chart|tool)|doesn'?t (support|provide|have)|"
    r"don'?t have .{0,30} tool|outside .{0,20} capabilities|not .{0,20} supported|"
    r"no tool .{0,30} (for|to)|beyond .{0,20} current)"
)

st.title("🤖 AI Analytics Assistant")
st.caption(
    "Ask anything about your funnel metrics. "
    "Powered by a **unified AI agent** with live data tools — no hallucinations."
)

dfs = load_all()

if "messages" not in st.session_state:
    st.session_state.messages = []


def _is_limitation(text: str) -> bool:
    """Return True if the assistant message indicates a capability gap."""
    return bool(_LIMITATION_PATTERNS.search(text))


def _get_preceding_user_question(msg_index: int) -> str:
    """Walk backwards from msg_index to find the user question that triggered it."""
    for i in range(msg_index - 1, -1, -1):
        m = st.session_state.messages[i]
        if m.get("role") == "user":
            c = m.get("content", "")
            if isinstance(c, list):
                c = " ".join(
                    b.get("text", "") for b in c
                    if isinstance(b, dict) and b.get("type") == "text"
                ).strip()
            return c
    return ""


def _build_feature_context(user_question: str, ai_response: str) -> str:
    """Build a pre-populated feature request from the conversation context."""
    ai_snippet = ai_response[:500] + ("..." if len(ai_response) > 500 else "")
    return (
        f"User asked: \"{user_question}\"\n\n"
        f"AI response: \"{ai_snippet}\"\n\n"
        f"Requested feature: Based on the above, the dashboard needs a new capability "
        f"to answer this type of question."
    )


@st.dialog("Request a Feature", width="large")
def _feature_request_dialog():
    context = st.session_state.get("feature_request_context", "")
    st.caption(
        "The description below was auto-populated from your conversation. "
        "Edit it if needed, then click Generate."
    )
    description = st.text_area(
        "What feature would you like?",
        value=context,
        height=180,
    )
    if st.button("Generate", type="primary"):
        if description.strip():
            from src.agents.feature_request import generate_feature_request
            with st.spinner("Generating PRD and code suggestion..."):
                output = generate_feature_request(description.strip())
            st.divider()
            st.markdown(output)
            st.download_button(
                label="Download as Markdown",
                data=output,
                file_name="feature_request.md",
                mime="text/markdown",
            )
        else:
            st.warning("Please describe the feature first.")


def _extract_text(content) -> str:
    """Extract plain text from a message content field."""
    if isinstance(content, list):
        return " ".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ).strip()
    return content or ""


# Starter question buttons
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

# Render message history
for idx, msg in enumerate(st.session_state.messages):
    role = msg.get("role")
    content = _extract_text(msg.get("content", ""))

    if role not in ("user", "assistant") or not content.strip():
        continue

    with st.chat_message(role):
        for fig_json in msg.get("chart_figures", []):
            import plotly.graph_objects as go
            st.plotly_chart(go.Figure(json.loads(fig_json)), width="stretch")
        st.markdown(content)

    if role == "assistant" and _is_limitation(content):
        user_q = _get_preceding_user_question(idx)
        if st.button("Request this as a feature", key=f"feat_req_{idx}", type="tertiary"):
            st.session_state.feature_request_context = _build_feature_context(user_q, content)
            _feature_request_dialog()

# Chat input handler
if prompt := st.chat_input("Ask about CVR, funnel steps, discounts, meal types…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.status("Analysing…", expanded=True) as status:
            try:
                result = run_turn(
                    messages=st.session_state.messages,
                    datasets=dfs,
                    max_history=_MAX_HISTORY,
                    status_container=status,
                )
                status.update(label="Done ✓", state="complete", expanded=False)
            except Exception as e:
                status.update(label="Error", state="error", expanded=True)
                st.error(f"An error occurred: {e}")
                st.stop()

        for fig in result.charts:
            st.plotly_chart(fig, width="stretch")

        response_text = st.write_stream(result.stream_gen)

    st.session_state.messages.append({
        "role": "assistant",
        "content": response_text,
        "chart_figures": [fig.to_json() for fig in result.charts],
    })

    if _is_limitation(response_text):
        user_q = prompt
        if st.button("Request this as a feature", key="feat_req_live", type="tertiary"):
            st.session_state.feature_request_context = _build_feature_context(user_q, response_text)
            _feature_request_dialog()

# Sidebar
with st.sidebar:
    st.header("Session")
    if st.button("🗑️ Clear conversation"):
        st.session_state.messages = []
        st.rerun()

    total = len(st.session_state.messages)
    st.caption(f"{total} messages total · last {_MAX_HISTORY} sent to AI")

    st.divider()
    st.markdown("**How it works**")
    st.markdown(
        "- 📊 Agent fetches exact numbers from live data\n"
        "- ✅ Validates metrics against known benchmarks\n"
        "- 🔍 Generates charts on request\n"
        "- 🚀 Streams response for fast first-token latency"
    )
