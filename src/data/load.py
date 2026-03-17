"""Load and cache the sales dataset."""

from pathlib import Path

import pandas as pd
import streamlit as st

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


@st.cache_data(show_spinner="Loading data...")
def get_sales_data(data_dir: str | None = None) -> pd.DataFrame:
    """Read the sales parquet file and return a DataFrame."""
    data_path = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
    parquet_file = data_path / "sales.parquet"
    if not parquet_file.exists():
        st.error(
            f"Data file not found at {parquet_file}. "
            "Run `python data/generate_data.py` first."
        )
        st.stop()
    return pd.read_parquet(parquet_file)
