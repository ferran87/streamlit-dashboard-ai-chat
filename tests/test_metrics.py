"""Tests for the metrics layer."""

import pandas as pd
import pytest

from src.metrics.compute import compute_all_metrics, compute_metric, list_metrics


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "order_date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "region": ["North America", "Europe", "Asia Pacific"],
            "product": ["Widget A", "Widget B", "Gadget Pro"],
            "channel": ["Online", "Retail", "Partner"],
            "quantity": [10, 5, 20],
            "unit_price": [100.0, 200.0, 50.0],
            "revenue": [1000.0, 1000.0, 1000.0],
            "customer_name": ["Alice", "Bob", "Charlie"],
        }
    )


def test_compute_metric_total_revenue(sample_df: pd.DataFrame):
    result = compute_metric("total_revenue", sample_df)
    assert "$3,000.00" in result


def test_compute_metric_total_orders(sample_df: pd.DataFrame):
    result = compute_metric("total_orders", sample_df)
    assert "3" in result


def test_compute_all_metrics_returns_all(sample_df: pd.DataFrame):
    results = compute_all_metrics(sample_df)
    registered = list_metrics()
    assert set(results.keys()) == {m["id"] for m in registered}


def test_unknown_metric_raises(sample_df: pd.DataFrame):
    with pytest.raises(KeyError):
        compute_metric("nonexistent_metric", sample_df)
