import streamlit as st

st.set_page_config(
    page_title="Dashboard + AI Chat",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Dashboard + AI Chat")
st.markdown(
    "Use the sidebar to navigate between the **Dashboard** "
    "(data visualizations) and the **AI Chat** (ask questions about the data)."
)
