"""Dashboard page: interactive data visualizations."""

import streamlit as st

from src.data.load import get_sales_data
from src.metrics.compute import compute_metric
from src.viz.charts import (
    price_distribution,
    revenue_by_region,
    revenue_over_time,
    top_products,
)

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("Sales Dashboard")

df = get_sales_data()

# --- Sidebar filters ---
st.sidebar.header("Filters")

date_min, date_max = df["order_date"].min().date(), df["order_date"].max().date()
date_range = st.sidebar.date_input(
    "Date range",
    value=(date_min, date_max),
    min_value=date_min,
    max_value=date_max,
)

regions = st.sidebar.multiselect(
    "Region",
    options=sorted(df["region"].unique()),
    default=sorted(df["region"].unique()),
)

products = st.sidebar.multiselect(
    "Product",
    options=sorted(df["product"].unique()),
    default=sorted(df["product"].unique()),
)

# --- Apply filters ---
import pandas as pd

mask = (
    (df["order_date"].dt.date >= date_range[0])
    & (df["order_date"].dt.date <= date_range[-1])
    & (df["region"].isin(regions))
    & (df["product"].isin(products))
)
filtered = df.loc[mask]

# --- KPI row (from metrics layer) ---
k1, k2, k3 = st.columns(3)
k1.metric("Total Revenue", compute_metric("total_revenue", filtered))
k2.metric("Total Orders", compute_metric("total_orders", filtered))
k3.metric("Avg Order Value", compute_metric("avg_order_value", filtered))

# --- Charts ---
c1, c2 = st.columns(2)
c1.plotly_chart(revenue_over_time(filtered), use_container_width=True)
c2.plotly_chart(top_products(filtered), use_container_width=True)

c3, c4 = st.columns(2)
c3.plotly_chart(revenue_by_region(filtered), use_container_width=True)
c4.plotly_chart(price_distribution(filtered), use_container_width=True)
