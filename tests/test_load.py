"""Smoke tests for data generation and loading."""

from pathlib import Path

import pandas as pd
import pytest


def test_generate_data():
    """Verify generate_data produces a valid DataFrame."""
    from data.generate_data import generate

    df = generate()
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    expected_cols = {
        "order_date", "region", "product", "channel",
        "quantity", "unit_price", "revenue", "customer_name",
    }
    assert expected_cols.issubset(set(df.columns))
