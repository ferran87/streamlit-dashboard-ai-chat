"""Funnel deep-dive with date, channel, and device filters."""

import streamlit as st
import pandas as pd
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

    dates = pd.to_datetime(dfs["sessions"]["session_date"])
    min_date, max_date = dates.min().date(), dates.max().date()
    date_range = st.date_input(
        "Date range",
        value=[min_date, max_date],
        min_value=min_date,
        max_value=max_date,
    )

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
dr = tuple(date_range) if len(date_range) == 2 else None

# ---------------------------------------------------------------------------
# Funnel CTR
# ---------------------------------------------------------------------------
st.subheader("Funnel Step CTR")
st.caption("Green = above benchmark  |  Red = below benchmark")
funnel_df = metrics.get_funnel_ctr(
    dfs["funnel_steps"], channel=channel, device=device,
    date_range=dr, df_sessions=dfs["sessions"],
)
st.plotly_chart(charts.funnel_steps_bar(funnel_df), width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# Drop-off waterfall
# ---------------------------------------------------------------------------
st.subheader("Sessions Lost per Step")
drop_df = metrics.get_funnel_drop_off(dfs["funnel_steps"])
st.plotly_chart(charts.funnel_drop_off_waterfall(drop_df), width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# CVR by channel & device
# ---------------------------------------------------------------------------
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("CVR by Channel")
    ch_df = metrics.get_conversion_by_channel(dfs["sessions"], dfs["activations"])
    st.plotly_chart(charts.cvr_by_channel_bar(ch_df), width="stretch")

with col_right:
    st.subheader("CVR by Device")
    dev_df = metrics.get_conversion_by_device(dfs["sessions"], dfs["activations"])
    st.plotly_chart(charts.cvr_by_device_bar(dev_df), width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# Heatmap
# ---------------------------------------------------------------------------
st.subheader("Time on Step × Device (seconds)")
st.plotly_chart(
    charts.funnel_ctr_heatmap(dfs["funnel_steps"], dfs["sessions"]),
    width="stretch",
)
