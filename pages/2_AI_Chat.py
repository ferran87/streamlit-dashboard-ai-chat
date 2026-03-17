"""AI Chat page: ask questions about the data."""

import streamlit as st

from src.chat.context import build_context
from src.chat.ui import init_chat_state, render_chat_history, render_suggested_questions
from src.data.load import get_sales_data
from src.llm import complete

st.set_page_config(page_title="AI Chat", page_icon="💬", layout="wide")
st.title("AI Chat")
st.caption(
    "Ask questions about the sales data. Numbers come from pre-computed metrics "
    "to avoid hallucination."
)

df = get_sales_data()
init_chat_state()

render_chat_history()
suggested = render_suggested_questions()

user_input = st.chat_input("Ask a question about the data...")
question = suggested or user_input

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            context = build_context(df)
            try:
                answer = complete(context=context, user_message=question)
            except ValueError as exc:
                answer = f"⚠️ {exc}"
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
