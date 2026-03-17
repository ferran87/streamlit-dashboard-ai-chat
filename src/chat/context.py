"""Build the context string injected into the LLM prompt."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data.schema import schema_as_text
from src.metrics.compute import compute_all_metrics


@st.cache_data(show_spinner=False)
def build_context(df: pd.DataFrame, extra_metrics: dict | None = None) -> str:
    """Return a context string with schema, summary stats, pre-computed metrics, and a sample."""
    parts: list[str] = []

    parts.append("=== DATA SCHEMA ===")
    parts.append(schema_as_text())

    parts.append("\n=== SUMMARY STATISTICS ===")
    parts.append(f"Total rows: {len(df):,}")
    parts.append(f"Date range: {df['order_date'].min().date()} to {df['order_date'].max().date()}")
    parts.append(f"Regions: {', '.join(sorted(df['region'].unique()))}")
    parts.append(f"Products: {', '.join(sorted(df['product'].unique()))}")

    parts.append("\n=== PRE-COMPUTED METRICS (use only these numbers) ===")
    metrics = compute_all_metrics(df)
    if extra_metrics:
        metrics.update(extra_metrics)
    for metric_id, result in metrics.items():
        parts.append(f"[{metric_id}]: {result}")

    parts.append("\n=== SAMPLE ROWS (first 15) ===")
    parts.append(df.head(15).to_markdown(index=False))

    return "\n".join(parts)
