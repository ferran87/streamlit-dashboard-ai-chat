"""AI Analytics Assistant — unified agent with streaming and inline charts."""

import json
import re
import threading
from datetime import datetime
from pathlib import Path
import streamlit as st
from data.loader import load_all
from src.agents.unified import run_turn, dispatch_chart_tool

_FEATURE_REQUESTS_DIR = Path("docs/feature_requests")
_MAX_HISTORY = 20

_LIMITATION_PATTERNS = re.compile(
    r"(?i)("
    r"I can'?t \w+|I cannot \w+|"
    r"not (available|possible|supported|currently)|"
    r"unfortunately|unable to|"
    r"none of the available|no available (chart|tool)|"
    r"doesn'?t (support|provide|have|include|offer)|"
    r"don'?t (have|include|support|offer)|"
    r"outside .{0,20} capabilities|beyond .{0,20} current|"
    r"no tool .{0,30} (for|to)|"
    r"available (chart|tool) types don'?t"
    r")"
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
    return bool(_LIMITATION_PATTERNS.search(text))


def _get_preceding_user_question(msg_index: int) -> str:
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
    ai_snippet = ai_response[:500] + ("..." if len(ai_response) > 500 else "")
    return (
        f"User asked: \"{user_question}\"\n\n"
        f"AI response: \"{ai_snippet}\"\n\n"
        f"Requested feature: Based on the above, the dashboard needs a new capability "
        f"to answer this type of question."
    )


def _submit_feature_request(user_question: str, ai_response: str):
    """Save a stub immediately, then generate the full PRD in a background thread."""
    _FEATURE_REQUESTS_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "_", user_question[:60].lower()).strip("_")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = _FEATURE_REQUESTS_DIR / f"{ts}_{slug}.md"

    stub = (
        f"# Feature Request\n\n"
        f"**Status:** Generating PRD...\n\n"
        f"**User question:** {user_question}\n\n"
        f"**AI limitation:** {ai_response[:300]}{'...' if len(ai_response) > 300 else ''}\n\n"
        f"---\n\n_Full PRD and code suggestion will be generated shortly._\n"
    )
    path.write_text(stub, encoding="utf-8")

    context = _build_feature_context(user_question, ai_response)

    def _generate():
        from src.agents.feature_request import generate_feature_request
        try:
            output = generate_feature_request(context)
            path.write_text(output, encoding="utf-8")
        except Exception as e:
            path.write_text(stub + f"\n\n**Generation failed:** {e}\n", encoding="utf-8")

    threading.Thread(target=_generate, daemon=True).start()


def _extract_text(content) -> str:
    if isinstance(content, list):
        return " ".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ).strip()
    return content or ""


def _render_feature_request_button(user_question: str, ai_response: str, key: str):
    """Render a prominent feature request callout with a button."""
    with st.container(border=True):
        col_text, col_btn = st.columns([3, 1])
        with col_text:
            st.markdown("**This capability isn't available yet.**")
        with col_btn:
            if st.button("Request Feature", key=key, type="primary"):
                _submit_feature_request(user_question, ai_response)
                st.toast("Feature request submitted! PRD is being generated in the background.", icon="✅")


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
        _render_feature_request_button(user_q, content, key=f"feat_req_{idx}")

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
        _render_feature_request_button(prompt, response_text, key="feat_req_live")

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
