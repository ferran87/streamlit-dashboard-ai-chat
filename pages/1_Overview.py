"""
pages/1_Overview.py
-------------------
Executive overview page.

Layout:
  Row 1: 4 KPI metric cards (Overall CVR, Total Activations, Avg Activation Value, Top Channel CVR)
  Row 2: Funnel steps bar (left) | Activation type pie (right)
  Row 3: Weekly session + activation trend (full width)

TODO (Cursor): Implement all chart sections below.
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
# TODO: Uncomment once metrics.get_kpi_summary() is implemented
# summary = metrics.get_kpi_summary(
#     dfs["sessions"], dfs["funnel_steps"],
#     dfs["activations"], dfs["meal_selections"], dfs["discounts"]
# )

# Row 1: metric cards
col1, col2, col3, col4 = st.columns(4)
# TODO: replace placeholder values with summary dict values
col1.metric("Overall CVR", "—%", help="Session → activation conversion rate")
col2.metric("Total Activations", "—", help="Confirmed orders in the period")
col3.metric("Avg Activation Value", "$—", help="Average basket value at activation")
col4.metric("Top Channel CVR", "—%", help="CVR of the best-performing acquisition channel")

st.divider()

# Row 2: funnel bar + pie
col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader("Funnel Step Drop-off")
    # TODO: st.plotly_chart(charts.funnel_steps_bar(metrics.get_funnel_ctr(dfs["funnel_steps"])), use_container_width=True)
    st.info("Implement `metrics.get_funnel_ctr()` and `charts.funnel_steps_bar()` to enable this chart.")

with col_right:
    st.subheader("Activations by Type")
    # TODO: st.plotly_chart(charts.activation_type_pie(metrics.get_activation_value_by_type(dfs["activations"])), use_container_width=True)
    st.info("Implement `metrics.get_activation_value_by_type()` and `charts.activation_type_pie()` to enable this chart.")

st.divider()

# Row 3: session volume trend
st.subheader("Weekly Session & Activation Volume")
# TODO: st.plotly_chart(charts.session_volume_trend(metrics.get_session_volume_trend(dfs["sessions"])), use_container_width=True)
st.info("Implement `metrics.get_session_volume_trend()` and `charts.session_volume_trend()` to enable this chart.")
