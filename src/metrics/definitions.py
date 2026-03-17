"""Metric registry: single source of truth for all computed metrics.

Each metric is a dict with:
  - id:          unique string key
  - description: human-readable explanation
  - compute_fn:  callable(df, **filters) -> str | number | pd.DataFrame
"""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd

MetricFn = Callable[..., Any]


def _total_revenue(df: pd.DataFrame, **_: Any) -> str:
    return f"${df['revenue'].sum():,.2f}"


def _total_orders(df: pd.DataFrame, **_: Any) -> str:
    return f"{len(df):,}"


def _avg_order_value(df: pd.DataFrame, **_: Any) -> str:
    return f"${df['revenue'].mean():,.2f}"


def _top_products_by_revenue(df: pd.DataFrame, *, n: int = 10, **_: Any) -> str:
    top = (
        df.groupby("product", as_index=False)["revenue"]
        .sum()
        .nlargest(n, "revenue")
    )
    lines = [f"  {i+1}. {r['product']}: ${r['revenue']:,.2f}" for i, r in top.iterrows()]
    return "\n".join(lines)


def _revenue_by_region(df: pd.DataFrame, **_: Any) -> str:
    by_region = (
        df.groupby("region", as_index=False)["revenue"]
        .sum()
        .sort_values("revenue", ascending=False)
    )
    lines = [f"  - {r['region']}: ${r['revenue']:,.2f}" for _, r in by_region.iterrows()]
    return "\n".join(lines)


def _top_products_by_quantity(df: pd.DataFrame, *, n: int = 5, **_: Any) -> str:
    top = (
        df.groupby("product", as_index=False)["quantity"]
        .sum()
        .nlargest(n, "quantity")
    )
    lines = [f"  {i+1}. {r['product']}: {r['quantity']:,} units" for i, r in top.iterrows()]
    return "\n".join(lines)


def _revenue_by_channel(df: pd.DataFrame, **_: Any) -> str:
    by_ch = (
        df.groupby("channel", as_index=False)["revenue"]
        .sum()
        .sort_values("revenue", ascending=False)
    )
    lines = [f"  - {r['channel']}: ${r['revenue']:,.2f}" for _, r in by_ch.iterrows()]
    return "\n".join(lines)


METRIC_REGISTRY: list[dict[str, Any]] = [
    {
        "id": "total_revenue",
        "description": "Sum of all revenue",
        "compute_fn": _total_revenue,
    },
    {
        "id": "total_orders",
        "description": "Total number of orders (rows)",
        "compute_fn": _total_orders,
    },
    {
        "id": "avg_order_value",
        "description": "Average revenue per order",
        "compute_fn": _avg_order_value,
    },
    {
        "id": "top_products_by_revenue",
        "description": "Top 10 products ranked by total revenue",
        "compute_fn": _top_products_by_revenue,
    },
    {
        "id": "revenue_by_region",
        "description": "Total revenue broken down by region",
        "compute_fn": _revenue_by_region,
    },
    {
        "id": "top_products_by_quantity",
        "description": "Top 5 products ranked by units sold",
        "compute_fn": _top_products_by_quantity,
    },
    {
        "id": "revenue_by_channel",
        "description": "Total revenue broken down by sales channel",
        "compute_fn": _revenue_by_channel,
    },
]
