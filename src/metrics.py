"""
src/metrics.py
--------------
Pure metric computation functions — NO Streamlit imports.
Each function accepts DataFrames and returns a DataFrame or scalar.
These are called by both src/charts.py and src/agents/tools.py.

All functions that accept optional filter parameters should return
unfiltered results when filters are None / "all".
"""

from __future__ import annotations

import pandas as pd
from typing import Optional


# ---------------------------------------------------------------------------
# Funnel Metrics
# ---------------------------------------------------------------------------

def get_funnel_ctr(
    df_funnel: pd.DataFrame,
    channel: Optional[str] = None,
    device: Optional[str] = None,
    date_range: Optional[tuple] = None,
    df_sessions: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Returns CTR per funnel step.

    TODO (Cursor): Implement.
    - Optionally filter by channel / device (requires joining df_sessions)
    - Optionally filter by date_range (tuple of date strings "YYYY-MM-DD")
    - For each consecutive pair of steps, compute CTR = sessions_reaching_next / sessions_reaching_current
    - exited_rate = 1 - ctr_to_next

    Returns DataFrame with columns:
        step (str), step_order (int), sessions_reached (int),
        ctr_to_next (float | None), exit_rate (float)
    """
    raise NotImplementedError("TODO: implement get_funnel_ctr()")


def get_overall_conversion_rate(
    df_sessions: pd.DataFrame,
    channel: Optional[str] = None,
    device: Optional[str] = None,
) -> float:
    """
    TODO (Cursor): Implement.
    Returns overall CVR = activated sessions / total sessions (as percentage 0–100).
    Optionally filter by channel and/or device.
    """
    raise NotImplementedError("TODO: implement get_overall_conversion_rate()")


def get_conversion_by_channel(
    df_sessions: pd.DataFrame,
    df_activations: pd.DataFrame,
) -> pd.DataFrame:
    """
    TODO (Cursor): Implement.
    Returns DataFrame: [channel, sessions (int), activations (int), cvr (float %)]
    Sorted descending by cvr.
    """
    raise NotImplementedError("TODO: implement get_conversion_by_channel()")


def get_conversion_by_device(
    df_sessions: pd.DataFrame,
    df_activations: pd.DataFrame,
) -> pd.DataFrame:
    """
    TODO (Cursor): Implement.
    Returns DataFrame: [device, sessions (int), activations (int), cvr (float %)]
    Sorted descending by cvr.
    """
    raise NotImplementedError("TODO: implement get_conversion_by_device()")


def get_funnel_drop_off(
    df_funnel: pd.DataFrame,
    df_sessions: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    TODO (Cursor): Implement.
    Returns DataFrame: [step, step_order, dropped_sessions (int), drop_pct (float %)]
    drop_pct = sessions that exited at this step / sessions that reached this step.
    """
    raise NotImplementedError("TODO: implement get_funnel_drop_off()")


# ---------------------------------------------------------------------------
# Activation Metrics
# ---------------------------------------------------------------------------

def get_activation_value_by_plan(df_activations: pd.DataFrame) -> pd.DataFrame:
    """
    TODO (Cursor): Implement.
    Returns DataFrame: [plan_name, count (int), avg_value (float), total_value (float)]
    Sorted descending by total_value.
    """
    raise NotImplementedError("TODO: implement get_activation_value_by_plan()")


def get_activation_value_by_type(df_activations: pd.DataFrame) -> pd.DataFrame:
    """
    TODO (Cursor): Implement.
    Returns DataFrame: [activation_type, count (int), avg_value (float), discount_rate (float %)]
    discount_rate = % of activations in this type that had has_discount=True.
    """
    raise NotImplementedError("TODO: implement get_activation_value_by_type()")


def get_discount_effectiveness(
    df_activations: pd.DataFrame,
    df_discounts: pd.DataFrame,
) -> pd.DataFrame:
    """
    TODO (Cursor): Implement.
    For each discount_code in df_discounts, compute:
      - used_count: how many activations used this code
      - avg_value_with: avg activation_value for activations WITH this code
      - avg_value_without: avg activation_value for activations WITHOUT any discount
      - uplift_pct: (avg_value_with - avg_value_without) / avg_value_without * 100

    Returns DataFrame: [discount_code, discount_type, used_count, avg_value_with,
                         avg_value_without, uplift_pct]
    Sorted descending by used_count.
    """
    raise NotImplementedError("TODO: implement get_discount_effectiveness()")


def get_meal_type_adoption(
    df_meals: pd.DataFrame,
    df_activations: pd.DataFrame,
) -> pd.DataFrame:
    """
    TODO (Cursor): Implement.
    Returns DataFrame: [meal_type, activation_count (int), pct_of_activations (float %)]
    activation_count = unique activations that included at least one meal of this type.
    pct_of_activations = activation_count / total_activations * 100.
    Sorted descending by activation_count.
    """
    raise NotImplementedError("TODO: implement get_meal_type_adoption()")


def get_activation_trend(
    df_activations: pd.DataFrame,
    granularity: str = "week",
) -> pd.DataFrame:
    """
    TODO (Cursor): Implement.
    Groups activations by period (week or month).
    Returns DataFrame: [period (str), activations (int), avg_value (float), total_revenue (float)]
    granularity: "week" or "month"
    """
    raise NotImplementedError("TODO: implement get_activation_trend()")


# ---------------------------------------------------------------------------
# Session Metrics
# ---------------------------------------------------------------------------

def get_session_volume_trend(df_sessions: pd.DataFrame) -> pd.DataFrame:
    """
    TODO (Cursor): Implement.
    Groups sessions by week.
    Returns DataFrame: [week (str), sessions (int), activated_sessions (int), cvr (float %)]
    """
    raise NotImplementedError("TODO: implement get_session_volume_trend()")


def get_kpi_summary(
    df_sessions: pd.DataFrame,
    df_funnel: pd.DataFrame,
    df_activations: pd.DataFrame,
    df_meals: pd.DataFrame,
    df_discounts: pd.DataFrame,
) -> dict:
    """
    TODO (Cursor): Implement.
    Computes all top-level KPIs and returns them as a flat dict.

    Keys to include:
      total_sessions, total_activations, overall_cvr (%), avg_activation_value,
      total_revenue, top_channel, top_channel_cvr (%),
      worst_funnel_step, worst_funnel_ctr (%),
      best_funnel_step, best_funnel_ctr (%),
      pct_with_discount (%), avg_discount_pct (%),
      date_min (str YYYY-MM-DD), date_max (str YYYY-MM-DD)
    """
    raise NotImplementedError("TODO: implement get_kpi_summary()")
