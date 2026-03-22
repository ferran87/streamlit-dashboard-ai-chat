"""
pages/1_Overview.py
-------------------
Executive overview page.

Layout:
  Row 1: 4 KPI metric cards
  Row 2: Funnel steps bar (left) | Activation type pie (right)
  Row 3: Weekly session + activation trend (full width)
"""

import streamlit as st
from data.loader import load_all
from src import metrics, charts

st.title("📊 Overview")
st.caption("HelloFresh funnel performance — last 12 months")

dfs = load_all()

# ---------------------------------------------------------------------------
# KPI summary
# ---------------------------------------------------------------------------
summary = metrics.get_kpi_summary(
    dfs["sessions"], dfs["funnel_steps"],
    dfs["activations"], dfs["meal_selections"], dfs["discounts"]
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Overall CVR", f'{summary["overall_cvr"]:.2f}%', help="Session → activation conversion rate")
col2.metric("Total Activations", f'{summary["total_activations"]:,}', help="Confirmed orders in the period")
col3.metric("Avg Activation Value", f'${summary["avg_activation_value"]:.2f}', help="Average basket value at activation")
col4.metric("Top Channel CVR", f'{summary["top_channel_cvr"]:.1f}% ({summary["top_channel"]})', help="CVR of the best-performing channel")

st.divider()

# ---------------------------------------------------------------------------
# Row 2: funnel bar + activation type pie
# ---------------------------------------------------------------------------
col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader("Funnel Step Drop-off")
    funnel_df = metrics.get_funnel_ctr(dfs["funnel_steps"])
    st.plotly_chart(charts.funnel_steps_bar(funnel_df), use_container_width=True)

with col_right:
    st.subheader("Activations by Type")
    type_df = metrics.get_activation_value_by_type(dfs["activations"])
    st.plotly_chart(charts.activation_type_pie(type_df), use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Row 3: session volume trend
# ---------------------------------------------------------------------------
st.subheader("Weekly Session & Activation Volume")
session_trend = metrics.get_session_volume_trend(dfs["sessions"])
st.plotly_chart(charts.session_volume_trend(session_trend), use_container_width=True)
