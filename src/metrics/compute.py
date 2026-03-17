"""Run metrics from the registry against a DataFrame."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.metrics.definitions import METRIC_REGISTRY


def compute_metric(metric_id: str, df: pd.DataFrame, **filters: Any) -> str:
    """Compute a single metric by id and return the result as a string."""
    for m in METRIC_REGISTRY:
        if m["id"] == metric_id:
            result = m["compute_fn"](df, **filters)
            return str(result)
    raise KeyError(f"Unknown metric: {metric_id}")


def compute_all_metrics(df: pd.DataFrame, **filters: Any) -> dict[str, str]:
    """Compute every registered metric and return {id: result_string}."""
    results: dict[str, str] = {}
    for m in METRIC_REGISTRY:
        results[m["id"]] = str(m["compute_fn"](df, **filters))
    return results


def list_metrics() -> list[dict[str, str]]:
    """Return a list of {id, description} for all registered metrics."""
    return [{"id": m["id"], "description": m["description"]} for m in METRIC_REGISTRY]
