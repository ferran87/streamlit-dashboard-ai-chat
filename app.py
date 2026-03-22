"""
HelloFresh Funnel Analytics Dashboard
Entry point — Streamlit multi-page navigation.
"""

from dotenv import load_dotenv
load_dotenv()

import streamlit as st

st.set_page_config(
    page_title="HelloFresh Funnel Analytics",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = {
    "Analytics": [
        st.Page("pages/1_Overview.py", title="Overview", icon=":material/dashboard:"),
        st.Page("pages/2_Funnel_Analysis.py", title="Funnel Analysis", icon=":material/filter_alt:"),
        st.Page("pages/3_Activation_Deep_Dive.py", title="Activation Deep Dive", icon=":material/bar_chart:"),
    ],
    "AI": [
        st.Page("pages/4_AI_Chat.py", title="AI Chat", icon=":material/chat:"),
    ],
}

pg = st.navigation(pages)
pg.run()
