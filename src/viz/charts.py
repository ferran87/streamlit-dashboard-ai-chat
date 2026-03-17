"""Plotly chart helpers for the dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def revenue_over_time(df: pd.DataFrame) -> go.Figure:
    """Line chart: daily revenue aggregated by order_date."""
    daily = df.groupby("order_date", as_index=False)["revenue"].sum()
    fig = px.line(
        daily,
        x="order_date",
        y="revenue",
        title="Revenue Over Time",
        labels={"order_date": "Date", "revenue": "Revenue (USD)"},
    )
    fig.update_layout(hovermode="x unified")
    return fig


def top_products(df: pd.DataFrame, n: int = 10) -> go.Figure:
    """Horizontal bar chart: top N products by total revenue."""
    top = (
        df.groupby("product", as_index=False)["revenue"]
        .sum()
        .nlargest(n, "revenue")
        .sort_values("revenue")
    )
    fig = px.bar(
        top,
        x="revenue",
        y="product",
        orientation="h",
        title=f"Top {n} Products by Revenue",
        labels={"revenue": "Revenue (USD)", "product": "Product"},
    )
    return fig


def revenue_by_region(df: pd.DataFrame) -> go.Figure:
    """Bar chart: total revenue per region."""
    by_region = df.groupby("region", as_index=False)["revenue"].sum().sort_values("revenue", ascending=False)
    fig = px.bar(
        by_region,
        x="region",
        y="revenue",
        title="Revenue by Region",
        labels={"region": "Region", "revenue": "Revenue (USD)"},
        color="region",
    )
    fig.update_layout(showlegend=False)
    return fig


def price_distribution(df: pd.DataFrame) -> go.Figure:
    """Histogram of unit prices."""
    fig = px.histogram(
        df,
        x="unit_price",
        nbins=40,
        title="Unit Price Distribution",
        labels={"unit_price": "Unit Price (USD)", "count": "Orders"},
    )
    return fig
