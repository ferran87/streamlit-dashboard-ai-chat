"""
pages/2_Funnel_Analysis.py
--------------------------
Funnel deep-dive with interactive filters.

Sidebar filters: date range, channel, device
Charts:
  - Funnel step CTR bar (green=healthy, red=below benchmark)
  - Drop-off waterfall
  - CVR by channel (grouped bar + CVR line)
  - CVR by device (bar)
  - Time on step × device heatmap

TODO (Cursor): Implement all chart sections below.
"""

import streamlit as st
from data.loader import load_all
from src import metrics, charts

st.title("🔍 Funnel Analysis")
st.caption("Step-by-step conversion analysis with channel and device breakdown")

dfs = load_all()

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Filters")
    # TODO: wire date range to filter df_sessions by session_date
    # date_range = st.date_input("Date range", value=[...])
    channel_filter = st.selectbox(
        "Channel",
        ["All", "organic_search", "paid_search", "paid_social", "email", "referral", "direct"]
    )
    device_filter = st.selectbox(
        "Device",
        ["All", "mobile", "desktop", "tablet"]
    )

channel = None if channel_filter == "All" else channel_filter
device = None if device_filter == "All" else device_filter

# ---------------------------------------------------------------------------
# Funnel CTR
# ---------------------------------------------------------------------------
st.subheader("Funnel Step CTR")
st.caption("Green = above benchmark  |  Red = below benchmark")
# TODO: st.plotly_chart(
#     charts.funnel_steps_bar(
#         metrics.get_funnel_ctr(dfs["funnel_steps"], channel=channel, device=device,
#                                df_sessions=dfs["sessions"])
#     ), use_container_width=True
# )
st.info("Implement `metrics.get_funnel_ctr()` and `charts.funnel_steps_bar()` to enable this chart.")

st.divider()

# Drop-off waterfall
st.subheader("Sessions Lost per Step")
# TODO: st.plotly_chart(charts.funnel_drop_off_waterfall(metrics.get_funnel_drop_off(...)), use_container_width=True)
st.info("Implement `metrics.get_funnel_drop_off()` and `charts.funnel_drop_off_waterfall()` to enable this chart.")

st.divider()

# CVR by channel & device
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("CVR by Channel")
    # TODO: st.plotly_chart(charts.cvr_by_channel_bar(metrics.get_conversion_by_channel(...)), use_container_width=True)
    st.info("Implement `metrics.get_conversion_by_channel()` and `charts.cvr_by_channel_bar()` to enable this chart.")

with col_right:
    st.subheader("CVR by Device")
    # TODO: st.plotly_chart(charts.cvr_by_device_bar(metrics.get_conversion_by_device(...)), use_container_width=True)
    st.info("Implement `metrics.get_conversion_by_device()` and `charts.cvr_by_device_bar()` to enable this chart.")

st.divider()

# Heatmap
st.subheader("Time on Step × Device (seconds)")
# TODO: st.plotly_chart(charts.funnel_ctr_heatmap(dfs["funnel_steps"], dfs["sessions"]), use_container_width=True)
st.info("Implement `charts.funnel_ctr_heatmap()` to enable this chart.")
