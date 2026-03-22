"""AI Analytics Assistant — unified agent with streaming and inline charts."""

import json
import streamlit as st
from data.loader import load_all
from src.agents.unified import run_turn, dispatch_chart_tool

_MAX_HISTORY = 20

st.title("🤖 AI Analytics Assistant")
st.caption(
    "Ask anything about your funnel metrics. "
    "Powered by a **unified AI agent** with live data tools — no hallucinations."
)

dfs = load_all()

if "messages" not in st.session_state:
    st.session_state.messages = []


@st.dialog("Request a Feature", width="large")
def _feature_request_dialog():
    st.caption(
        "Describe what you were trying to find out. The AI will generate "
        "a product spec and code suggestion for the development team."
    )
    description = st.text_area(
        "What feature would you like?",
        placeholder=(
            "e.g. I wanted to see how CVR changed week over week as a line chart, "
            "but the chat couldn't show me a time-series breakdown."
        ),
        height=120,
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

# Render message history — chart figures are stored as JSON to avoid recomputation
for msg in st.session_state.messages:
    role = msg.get("role")
    content = msg.get("content", "")

    if isinstance(content, list):
        content = " ".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ).strip()

    if role not in ("user", "assistant") or not content.strip():
        continue

    with st.chat_message(role):
        for fig_json in msg.get("chart_figures", []):
            import plotly.graph_objects as go
            st.plotly_chart(go.Figure(json.loads(fig_json)), width="stretch")
        st.markdown(content)

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

# Sidebar
with st.sidebar:
    st.header("Session")
    if st.button("🗑️ Clear conversation"):
        st.session_state.messages = []
        st.rerun()

    total = len(st.session_state.messages)
    st.caption(f"{total} messages total · last {_MAX_HISTORY} sent to AI")

    st.divider()
    st.subheader("Feature Request")
    st.caption("Describe a question the chat couldn't answer.")
    if st.button("Request a Feature", use_container_width=True):
        _feature_request_dialog()

    st.divider()
    st.markdown("**How it works**")
    st.markdown(
        "- 📊 Agent fetches exact numbers from live data\n"
        "- ✅ Validates metrics against known benchmarks\n"
        "- 🔍 Generates charts on request\n"
        "- 🚀 Streams response for fast first-token latency"
    )
