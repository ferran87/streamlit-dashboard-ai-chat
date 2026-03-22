"""
data/loader.py
--------------
Cached data loader for Streamlit pages.
Call load_all() once at the top of every page — Streamlit caches the result
for the lifetime of the process (no re-generation on page navigation).
"""

import streamlit as st

from data.generate import generate_all, OUTPUT_DIR
import pandas as pd


@st.cache_data(ttl=None, show_spinner="Loading data...")
def load_all() -> dict[str, pd.DataFrame]:
    """
    Load all 5 datasets from parquet (generating them first if needed).
    Returns a dict keyed by dataset name:
      "sessions", "funnel_steps", "activations", "meal_selections", "discounts"

    NOTE: @st.cache_data copies DataFrames on return to prevent mutation.
          Do not mutate the returned DataFrames in-place in page code.
    """
    files = {
        "sessions":        OUTPUT_DIR / "sessions.parquet",
        "funnel_steps":    OUTPUT_DIR / "funnel_steps.parquet",
        "activations":     OUTPUT_DIR / "activations.parquet",
        "meal_selections": OUTPUT_DIR / "meal_selections.parquet",
        "discounts":       OUTPUT_DIR / "discounts.parquet",
    }

    if not all(p.exists() for p in files.values()):
        return generate_all()

    return {k: pd.read_parquet(v) for k, v in files.items()}
