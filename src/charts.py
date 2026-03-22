"""Plotly figure builders — accepts DataFrames from src/metrics.py, returns Figures."""

from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

from src.metrics import _STEP_ORDER as STEP_ORDER


def _hex_alpha(hex_color: str, alpha: float) -> str:
    """Convert a 6-char hex color + alpha (0–1) to an rgba() string."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

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

_H_LEGEND = dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)

_CTR_BENCHMARKS = {
    "landing": 60, "menu_browse": 40, "plan_selection": 65,
    "delivery_settings": 75, "account_creation": 70, "payment": 78,
}


def _theme(fig: go.Figure, title: str, height: int = 400, legend: bool = False, **kw) -> go.Figure:
    """Apply dark theme and optional horizontal legend to a figure."""
    opts = {**DARK_LAYOUT, "title": title, "height": height, **kw}
    if legend:
        opts["legend"] = _H_LEGEND
    fig.update_layout(**opts)
    return fig


def funnel_steps_bar(df_funnel: pd.DataFrame) -> go.Figure:
    """Horizontal bar — sessions reached per step, coloured by exit rate."""
    df = df_funnel.copy()
    colors = []
    for _, row in df.iterrows():
        ctr = row["ctr_to_next"]
        step = row["step"]
        if ctr is None or pd.isna(ctr):
            colors.append(COLORS["primary"])
        elif ctr >= _CTR_BENCHMARKS.get(step, 60):
            colors.append(COLORS["green"])
        else:
            colors.append(COLORS["red"])

    fig = go.Figure(go.Bar(
        y=df["step"],
        x=df["sessions_reached"],
        orientation="h",
        marker_color=colors,
        text=[
            f'{int(r["sessions_reached"]):,}  (CTR {r["ctr_to_next"]:.1f}%)'
            if r["ctr_to_next"] is not None and not pd.isna(r["ctr_to_next"])
            else f'{int(r["sessions_reached"]):,}'
            for _, r in df.iterrows()
        ],
        textposition="auto",
        textfont=dict(color=COLORS["text"]),
    ))
    _theme(fig, "Funnel Steps — Sessions Reached",
           xaxis_title="Sessions",
           yaxis=dict(categoryorder="array", categoryarray=list(reversed(df["step"]))))
    return fig


def funnel_drop_off_waterfall(df_drop: pd.DataFrame) -> go.Figure:
    """Waterfall chart showing sessions lost at each step."""
    fig = go.Figure(go.Waterfall(
        x=df_drop["step"],
        y=[-d for d in df_drop["dropped_sessions"]],
        measure=["relative"] * len(df_drop),
        text=[f'-{int(d):,}' if d > 0 else '' for d in df_drop["dropped_sessions"]],
        textposition="outside",
        textfont=dict(color=COLORS["text"]),
        decreasing=dict(marker_color=COLORS["red"]),
        increasing=dict(marker_color=COLORS["green"]),
        totals=dict(marker_color=COLORS["primary"]),
        connector=dict(line=dict(color=COLORS["muted"], width=1)),
    ))
    _theme(fig, "Sessions Lost per Funnel Step", yaxis_title="Sessions dropped", showlegend=False)
    return fig


def activation_trend_line(df_trend: pd.DataFrame) -> go.Figure:
    """Dual-axis line: activations count (left) and avg value (right)."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=df_trend["period"], y=df_trend["activations"],
            name="Activations", mode="lines+markers",
            line=dict(color=COLORS["primary"], width=2),
            marker=dict(size=5),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df_trend["period"], y=df_trend["avg_value"],
            name="Avg Value ($)", mode="lines+markers",
            line=dict(color=COLORS["teal"], width=2, dash="dot"),
            marker=dict(size=5),
        ),
        secondary_y=True,
    )

    _theme(fig, "Activation Trend", legend=True)
    fig.update_yaxes(title_text="Activations", secondary_y=False, gridcolor=COLORS["surface"])
    fig.update_yaxes(title_text="Avg Value ($)", secondary_y=True, gridcolor=COLORS["surface"])
    fig.update_xaxes(gridcolor=COLORS["surface"])
    return fig


def activation_type_pie(df_type: pd.DataFrame) -> go.Figure:
    """Pie of activation_type distribution."""
    palette = [COLORS["primary"], COLORS["teal"], COLORS["orange"], COLORS["yellow"]]
    fig = go.Figure(go.Pie(
        labels=df_type["activation_type"],
        values=df_type["count"],
        hole=0.4,
        marker=dict(colors=palette[:len(df_type)]),
        textinfo="label+percent",
        textfont=dict(color=COLORS["text"]),
    ))
    _theme(fig, "Activations by Type", showlegend=True,
           legend=dict(font=dict(color=COLORS["text"])))
    return fig


def cvr_by_channel_bar(df_channel: pd.DataFrame) -> go.Figure:
    """Grouped bar (sessions + activations) with CVR line on secondary axis."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    bar_colors = [CHANNEL_COLORS.get(ch, COLORS["primary"]) for ch in df_channel["channel"]]

    fig.add_trace(
        go.Bar(
            x=df_channel["channel"], y=df_channel["sessions"],
            name="Sessions", marker_color=[_hex_alpha(c, 0.5) for c in bar_colors],
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            x=df_channel["channel"], y=df_channel["activations"],
            name="Activations", marker_color=bar_colors,
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df_channel["channel"], y=df_channel["cvr"],
            name="CVR %", mode="lines+markers+text",
            text=[f'{v:.1f}%' for v in df_channel["cvr"]],
            textposition="top center",
            textfont=dict(color=COLORS["yellow"]),
            line=dict(color=COLORS["yellow"], width=2),
            marker=dict(size=8, color=COLORS["yellow"]),
        ),
        secondary_y=True,
    )

    _theme(fig, "Conversion by Channel", height=420, legend=True, barmode="group")
    fig.update_yaxes(title_text="Count", secondary_y=False, gridcolor=COLORS["surface"])
    fig.update_yaxes(title_text="CVR %", secondary_y=True, gridcolor=COLORS["surface"])
    fig.update_xaxes(gridcolor=COLORS["surface"])
    return fig


def cvr_by_device_bar(df_device: pd.DataFrame) -> go.Figure:
    """Horizontal bar of CVR by device."""
    device_colors = {
        "desktop": COLORS["green"],
        "mobile": COLORS["primary"],
        "tablet": COLORS["orange"],
    }
    colors = [device_colors.get(d, COLORS["muted"]) for d in df_device["device"]]

    fig = go.Figure(go.Bar(
        y=df_device["device"],
        x=df_device["cvr"],
        orientation="h",
        marker_color=colors,
        text=[f'{v:.2f}%' for v in df_device["cvr"]],
        textposition="auto",
        textfont=dict(color=COLORS["text"]),
    ))
    _theme(fig, "Conversion Rate by Device", height=300, xaxis_title="CVR %")
    return fig


def funnel_ctr_heatmap(df_funnel: pd.DataFrame, df_sessions: pd.DataFrame) -> go.Figure:
    """Heatmap of time_on_step (seconds) by step × device."""
    merged = df_funnel.merge(
        df_sessions[["session_id", "device"]], on="session_id", how="left"
    )
    pivot = merged.pivot_table(
        values="time_on_step_seconds",
        index="step_name",
        columns="device",
        aggfunc="mean",
    )
    pivot = pivot.reindex(STEP_ORDER)

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale="RdYlGn_r",
        text=np.round(pivot.values, 1),
        texttemplate="%{text:.0f}s",
        textfont=dict(color=COLORS["text"]),
        colorbar=dict(title="Seconds"),
    ))
    _theme(fig, "Avg Time on Step by Device (seconds)", height=420)
    return fig


def activation_value_by_plan_bar(df_plan: pd.DataFrame) -> go.Figure:
    """Horizontal bar sorted by total_value, annotated with avg_value."""
    df = df_plan.sort_values("total_value", ascending=True)
    plan_colors = [COLORS["primary"], COLORS["teal"], COLORS["green"],
                   COLORS["orange"], COLORS["yellow"], COLORS["muted"]]

    fig = go.Figure(go.Bar(
        y=df["plan_name"],
        x=df["total_value"],
        orientation="h",
        marker_color=plan_colors[:len(df)],
        text=[f'${tv:,.0f}  (avg ${av:.0f})' for tv, av in zip(df["total_value"], df["avg_value"])],
        textposition="auto",
        textfont=dict(color=COLORS["text"]),
    ))
    _theme(fig, "Total Activation Value by Plan", height=380, xaxis_title="Total Revenue ($)")
    return fig


def meal_type_adoption_bar(df_meal: pd.DataFrame) -> go.Figure:
    """Horizontal bar: meal_type vs pct_of_activations."""
    df = df_meal.sort_values("pct_of_activations", ascending=True)
    fig = go.Figure(go.Bar(
        y=df["meal_type"],
        x=df["pct_of_activations"],
        orientation="h",
        marker_color=COLORS["teal"],
        text=[f'{v:.1f}%' for v in df["pct_of_activations"]],
        textposition="auto",
        textfont=dict(color=COLORS["text"]),
    ))
    _theme(fig, "Meal Type Adoption (% of activations)", height=350, xaxis_title="% of Activations")
    return fig


def discount_effectiveness_table(df_discount: pd.DataFrame) -> go.Figure:
    """Plotly table with colour-coded uplift column."""
    uplift_colors = [
        COLORS["green"] if v > 0 else COLORS["red"]
        for v in df_discount["uplift_pct"]
    ]
    header_color = COLORS["surface"]
    cell_color = COLORS["bg"]

    fig = go.Figure(go.Table(
        header=dict(
            values=["Code", "Type", "Used", "Avg $ With", "Avg $ Without", "Uplift %"],
            fill_color=header_color,
            font=dict(color=COLORS["text"], size=13),
            align="left",
        ),
        cells=dict(
            values=[
                df_discount["discount_code"],
                df_discount["discount_type"],
                df_discount["used_count"],
                [f'${v:.2f}' for v in df_discount["avg_value_with"]],
                [f'${v:.2f}' for v in df_discount["avg_value_without"]],
                [f'{v:+.1f}%' for v in df_discount["uplift_pct"]],
            ],
            fill_color=[
                [cell_color] * len(df_discount),
                [cell_color] * len(df_discount),
                [cell_color] * len(df_discount),
                [cell_color] * len(df_discount),
                [cell_color] * len(df_discount),
                uplift_colors,
            ],
            font=dict(color=COLORS["text"], size=12),
            align="left",
            height=30,
        ),
    ))
    _theme(fig, "Discount Effectiveness", height=max(350, 60 + len(df_discount) * 32))
    return fig


def cuisine_pie(df_meals: pd.DataFrame) -> go.Figure:
    """Pie of cuisine distribution across all meal selections."""
    counts = df_meals["cuisine"].value_counts().reset_index()
    counts.columns = ["cuisine", "count"]
    palette = [COLORS["primary"], COLORS["teal"], COLORS["orange"],
               COLORS["yellow"], COLORS["green"]]
    fig = go.Figure(go.Pie(
        labels=counts["cuisine"],
        values=counts["count"],
        hole=0.4,
        marker=dict(colors=palette[:len(counts)]),
        textinfo="label+percent",
        textfont=dict(color=COLORS["text"]),
    ))
    _theme(fig, "Cuisine Breakdown", showlegend=True,
           legend=dict(font=dict(color=COLORS["text"])))
    return fig


def session_volume_trend(df_sessions_trend: pd.DataFrame) -> go.Figure:
    """Stacked area: activated vs non-activated sessions per week."""
    df = df_sessions_trend.copy()
    df["non_activated"] = df["sessions"] - df["activated_sessions"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["week"], y=df["activated_sessions"],
        name="Activated", stackgroup="one",
        fillcolor=_hex_alpha(COLORS["green"], 0.5),
        line=dict(color=COLORS["green"], width=1),
    ))
    fig.add_trace(go.Scatter(
        x=df["week"], y=df["non_activated"],
        name="Non-activated", stackgroup="one",
        fillcolor=_hex_alpha(COLORS["primary"], 0.25),
        line=dict(color=COLORS["primary"], width=1),
    ))
    _theme(fig, "Weekly Session Volume", legend=True, yaxis_title="Sessions")
    fig.update_xaxes(gridcolor=COLORS["surface"])
    fig.update_yaxes(gridcolor=COLORS["surface"])
    return fig
