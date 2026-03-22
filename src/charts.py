"""
src/charts.py
-------------
Plotly figure builders — NO Streamlit imports.
Each function accepts a pre-computed DataFrame (from src/metrics.py)
and returns a plotly.graph_objects.Figure.

Consistent dark theme: use layout updates matching .streamlit/config.toml
  paper_bgcolor="#0f172a", plot_bgcolor="#1e293b", font_color="#f8fafc"
Primary accent colour: #6366f1 (indigo)
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd

# Shared colour palette
COLORS = {
    "primary":     "#6366f1",
    "green":       "#22c55e",
    "red":         "#ef4444",
    "orange":      "#f97316",
    "teal":        "#14b8a6",
    "yellow":      "#eab308",
    "bg":          "#0f172a",
    "surface":     "#1e293b",
    "text":        "#f8fafc",
    "muted":       "#94a3b8",
}

DARK_LAYOUT = dict(
    paper_bgcolor=COLORS["bg"],
    plot_bgcolor=COLORS["surface"],
    font=dict(color=COLORS["text"]),
    margin=dict(l=40, r=20, t=50, b=40),
)

CHANNEL_COLORS = {
    "organic_search": COLORS["green"],
    "paid_search":    COLORS["primary"],
    "paid_social":    COLORS["teal"],
    "email":          COLORS["yellow"],
    "referral":       COLORS["orange"],
    "direct":         COLORS["muted"],
}


def funnel_steps_bar(df_funnel: pd.DataFrame) -> go.Figure:
    """
    TODO (Cursor): Implement.
    Horizontal bar chart — sessions reached per funnel step.
    Colour each bar by exit_rate (green=low drop, red=high drop).
    Add CTR annotation on each bar.
    Input: output of metrics.get_funnel_ctr()
    """
    raise NotImplementedError("TODO: implement funnel_steps_bar()")


def funnel_drop_off_waterfall(df_drop: pd.DataFrame) -> go.Figure:
    """
    TODO (Cursor): Implement.
    go.Waterfall showing sessions lost at each funnel step.
    Input: output of metrics.get_funnel_drop_off()
    """
    raise NotImplementedError("TODO: implement funnel_drop_off_waterfall()")


def activation_trend_line(df_trend: pd.DataFrame) -> go.Figure:
    """
    TODO (Cursor): Implement.
    Dual-axis line chart: left=activations count, right=avg activation value.
    Input: output of metrics.get_activation_trend()
    """
    raise NotImplementedError("TODO: implement activation_trend_line()")


def activation_type_pie(df_activations: pd.DataFrame) -> go.Figure:
    """
    TODO (Cursor): Implement.
    go.Pie of activation_type distribution.
    Input: output of metrics.get_activation_value_by_type()
    """
    raise NotImplementedError("TODO: implement activation_type_pie()")


def cvr_by_channel_bar(df_channel: pd.DataFrame) -> go.Figure:
    """
    TODO (Cursor): Implement.
    Grouped bar: sessions and activations side-by-side per channel,
    with CVR % as a line on secondary axis.
    Input: output of metrics.get_conversion_by_channel()
    """
    raise NotImplementedError("TODO: implement cvr_by_channel_bar()")


def cvr_by_device_bar(df_device: pd.DataFrame) -> go.Figure:
    """
    TODO (Cursor): Implement.
    Horizontal bar chart of CVR by device.
    Color code vs benchmark (mobile 30–40% lower than desktop is expected).
    Input: output of metrics.get_conversion_by_device()
    """
    raise NotImplementedError("TODO: implement cvr_by_device_bar()")


def funnel_ctr_heatmap(df_funnel: pd.DataFrame, df_sessions: pd.DataFrame) -> go.Figure:
    """
    TODO (Cursor): Implement.
    go.Heatmap of CTR by step (rows) × device (columns).
    Input: df_funnel from generate, df_sessions for device join.
    colorscale="RdYlGn", annotate cells with pct values.
    """
    raise NotImplementedError("TODO: implement funnel_ctr_heatmap()")


def activation_value_by_plan_bar(df_plan: pd.DataFrame) -> go.Figure:
    """
    TODO (Cursor): Implement.
    Horizontal bar chart sorted by total_value descending.
    Color by plan name. Show avg_value as text annotation.
    Input: output of metrics.get_activation_value_by_plan()
    """
    raise NotImplementedError("TODO: implement activation_value_by_plan_bar()")


def meal_type_adoption_bar(df_meal: pd.DataFrame) -> go.Figure:
    """
    TODO (Cursor): Implement.
    Horizontal bar chart: meal_type vs pct_of_activations.
    Input: output of metrics.get_meal_type_adoption()
    """
    raise NotImplementedError("TODO: implement meal_type_adoption_bar()")


def discount_effectiveness_table(df_discount: pd.DataFrame) -> go.Figure:
    """
    TODO (Cursor): Implement.
    go.Table with colour-coded uplift_pct column
    (green if positive, red if negative).
    Input: output of metrics.get_discount_effectiveness()
    """
    raise NotImplementedError("TODO: implement discount_effectiveness_table()")


def cuisine_pie(df_meals: pd.DataFrame) -> go.Figure:
    """
    TODO (Cursor): Implement.
    go.Pie of cuisine distribution across all meal selections.
    Input: raw df_meals (meal_selections.parquet).
    """
    raise NotImplementedError("TODO: implement cuisine_pie()")


def session_volume_trend(df_sessions_trend: pd.DataFrame) -> go.Figure:
    """
    TODO (Cursor): Implement.
    Stacked area: activated sessions vs non-activated sessions per week.
    Input: output of metrics.get_session_volume_trend()
    """
    raise NotImplementedError("TODO: implement session_volume_trend()")
