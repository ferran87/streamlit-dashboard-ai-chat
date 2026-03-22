## 📋 Product Requirements Spec

### Problem
The AI Chat cannot produce a weekly session/conversion trend broken down by device, forcing users to choose between temporal granularity (weekly trend) and device segmentation — but not both simultaneously.

### User Story
As a dashboard user, I want to see weekly conversion and session volume trends broken down by device (desktop, mobile, tablet) so that I can identify whether performance changes over time are driven by a specific device segment.

### Proposed Solution
Add a new analytics metric function `get_session_volume_trend_by_device` that pivots the weekly trend by device, producing one row per (week, device) pair. Expose this as a new AI tool `get_session_volume_trend_by_device`, and add a corresponding multi-line chart type `session_volume_trend_by_device` that renders one line per device over time.

### Success Criteria
- The AI Chat can answer: "Show me the weekly conversion trend broken down by device"
- The chart renders a distinct line (or grouped bar) per device across weekly periods, with CVR, sessions, and activated sessions all visible
- The tool supports `date_range_start` / `date_range_end` filtering, consistent with all other analytics tools

---

## 🛠️ Code Suggestion

### Files to Modify
| File | Change |
|---|---|
| `src/metrics.py` | Add `get_session_volume_trend_by_device()` function |
| `src/charts.py` | Add `build_session_volume_trend_by_device()` chart builder |
| `src/agents/tools.py` | Add new entry to `ANALYTICS_TOOLS` and new chart type to `GENERATE_CHART_TOOL` enum |
| `src/agents/unified.py` | Add `elif` branch in `_dispatch_analytics_tool()` and register chart in `_CHART_REGISTRY` |

---

### Step-by-step Implementation

---

#### Step 1 — `src/metrics.py`

Add after the existing `get_session_volume_trend` function:

```python
def get_session_volume_trend_by_device(
    df_sessions: pd.DataFrame,
    df_activations: pd.DataFrame,
    granularity: str = "week",
) -> pd.DataFrame:
    """
    Returns weekly (or daily/monthly) session volume and CVR broken down by device.
    Output columns: [period, device, sessions, activated_sessions, cvr]
    """
    df = df_sessions.copy()
    df["session_date"] = pd.to_datetime(df["session_date"])

    # Build period label using the same granularity logic as get_session_volume_trend
    if granularity == "day":
        df["period"] = df["session_date"].dt.strftime("%Y-%m-%d")
    elif granularity == "month":
        df["period"] = df["session_date"].dt.to_period("M").astype(str)
    else:  # default: week
        df["period"] = (
            df["session_date"]
            .dt.to_period("W")
            .apply(lambda p: p.start_time.strftime("%Y-%m-%d"))
        )

    # Aggregate per (period, device)
    grouped = (
        df.groupby(["period", "device"])
        .agg(
            sessions=("session_id", "count"),
            activated_sessions=("activated", "sum"),
        )
        .reset_index()
    )

    grouped["cvr"] = (
        grouped["activated_sessions"] / grouped["sessions"]
    ).round(4)

    # Ensure chronological order
    grouped = grouped.sort_values(["period", "device"]).reset_index(drop=True)

    return grouped
```

---

#### Step 2 — `src/charts.py`

Add after the existing `build_session_volume_trend` function:

```python
def build_session_volume_trend_by_device(datasets: dict, **kw) -> go.Figure:
    """
    Multi-line chart: weekly CVR (or sessions) trend with one line per device.
    Supports optional metric kwarg: 'cvr' (default) | 'sessions' | 'activated_sessions'
    """
    from src.metrics import get_session_volume_trend_by_device

    df_sessions = datasets["sessions"]
    df_activations = datasets["activations"]
    granularity = kw.get("granularity", "week")
    metric = kw.get("metric", "cvr")  # what to plot on Y axis

    df = get_session_volume_trend_by_device(df_sessions, df_activations, granularity)

    if df.empty:
        fig = go.Figure()
        fig.update_layout(title="No data available for the selected range.")
        return fig

    # Human-readable labels
    metric_labels = {
        "cvr": "Conversion Rate",
        "sessions": "Sessions",
        "activated_sessions": "Activated Sessions",
    }
    y_label = metric_labels.get(metric, metric)

    # One trace per device
    devices = sorted(df["device"].unique())
    # Colour palette consistent with other multi-series charts
    palette = ["#FF6B35", "#2EC4B6", "#8B5CF6", "#F59E0B", "#10B981"]

    fig = go.Figure()

    for i, device in enumerate(devices):
        df_dev = df[df["device"] == device].sort_values("period")

        y_values = df_dev[metric]
        if metric == "cvr":
            # Express as percentage for readability
            y_values = (y_values * 100).round(2)

        fig.add_trace(
            go.Scatter(
                x=df_dev["period"],
                y=y_values,
                mode="lines+markers",
                name=device.capitalize(),
                line=dict(color=palette[i % len(palette)], width=2),
                marker=dict(size=6),
                hovertemplate=(
                    f"<b>{device.capitalize()}</b><br>"
                    "Week: %{x}<br>"
                    + (
                        f"{y_label}: %{{y:.1f}}%<extra></extra>"
                        if metric == "cvr"
                        else f"{y_label}: %{{y:,}}<extra></extra>"
                    )
                ),
            )
        )

    y_axis_format = ".1f" if metric == "cvr" else ","
    y_axis_suffix = "%" if metric == "cvr" else ""

    fig.update_layout(
        title=dict(
            text=f"Weekly {y_label} by Device",
            font=dict(size=16, color="#1F2937"),
        ),
        xaxis=dict(
            title="Week Starting",
            tickangle=-30,
            showgrid=False,
        ),
        yaxis=dict(
            title=f"{y_label}{' (%)' if metric == 'cvr' else ''}",
            tickformat=y_axis_format,
            ticksuffix=y_axis_suffix,
            showgrid=True,
            gridcolor="#F3F4F6",
        ),
        legend=dict(
            title="Device",
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        hovermode="x unified",
        height=420,
        margin=dict(l=60, r=30, t=80, b=60),
    )

    return fig
```

---

#### Step 3 — `src/agents/tools.py`

**3a.** Add a new entry inside the `ANALYTICS_TOOLS` list:

```python
{
    "name": "get_session_volume_trend_by_device",
    "description": (
        "Returns weekly session volume and conversion rate (CVR) broken down by device "
        "(e.g. desktop, mobile, tablet). Use this when the user wants a time-series trend "
        "split by device — i.e. they want BOTH a weekly view AND a per-device breakdown. "
        "Returns columns: period, device, sessions, activated_sessions, cvr."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "granularity": {
                "type": "string",
                "enum": ["day", "week", "month"],
                "description": "Time granularity for grouping. Defaults to 'week'.",
            },
            **_DATE_PROPS,  # date_range_start, date_range_end for free
        },
        "required": [],
    },
},
```

**3b.** Inside `GENERATE_CHART_TOOL`, add `"session_volume_trend_by_device"` to the `chart_type` enum list and update its description:

```python
# Locate the chart_type property in GENERATE_CHART_TOOL's input_schema and add the new value:
{
    "name": "session_volume_trend_by_device",
    # ... add to the existing enum list:
    # "enum": [..., "session_volume_trend_by_device"]
}
```

The full updated `chart_type` enum should include:

```python
"enum": [
    "funnel_steps_bar",
    "funnel_drop_off_waterfall",
    "activation_trend_line",
    "activation_type_pie",
    "cvr_by_channel_bar",
    "cvr_by_device_bar",
    "activation_value_by_plan",
    "meal_type_adoption_bar",
    "discount_effectiveness",
    "session_volume_trend",
    "session_volume_trend_by_device",   # ← NEW
],
```

Also update the `chart_type` description to include a note:

```python
"description": (
    "The type of chart to generate. Use 'session_volume_trend_by_device' when the user "
    "wants weekly trends split by device (multi-line, one line per device)."
    # ... keep existing description text
),
```

And add `metric` to the chart tool's optional properties:

```python
"metric": {
    "type": "string",
    "enum": ["cvr", "sessions", "activated_sessions"],
    "description": (
        "For 'session_volume_trend_by_device': which metric to plot on the Y-axis. "
        "Defaults to 'cvr'. Use 'sessions' for raw volume, 'activated_sessions' for "
        "converted session counts."
    ),
},
```

---

#### Step 4 — `src/agents/unified.py`

**4a.** In `_dispatch_analytics_tool()`, add an `elif` branch:

```python
elif tool_name == "get_session_volume_trend_by_device":
    granularity = tool_input.get("granularity", "week")
    result_df = metrics.get_session_volume_trend_by_device(
        datasets["sessions"],
        datasets["activations"],
        granularity=granularity,
    )
    return result_df.to_dict(orient="records")
```

**4b.** In `_CHART_REGISTRY` dict, register the new builder:

```python
_CHART_REGISTRY = {
    # ... existing entries ...
    "session_volume_trend_by_device": build_session_volume_trend_by_device,  # ← NEW
}
```

**4c.** Make sure the import at the top of `unified.py` includes the new chart builder:

```python
from src.charts import (
    build_funnel_steps_bar,
    build_funnel_drop_off_waterfall,
    build_activation_trend_line,
    build_activation_type_pie,
    build_cvr_by_channel_bar,
    build_cvr_by_device_bar,
    build_activation_value_by_plan,
    build_meal_type_adoption_bar,
    build_discount_effectiveness,
    build_session_volume_trend,
    build_session_volume_trend_by_device,   # ← NEW
)
```

**4d.** In `dispatch_chart_tool`, pass through the `metric` kwarg so it reaches the builder:

```python
def dispatch_chart_tool(tool_input: dict, datasets: dict) -> go.Figure:
    chart_type = tool_input.get("chart_type")
    builder = _CHART_REGISTRY.get(chart_type)
    if builder is None:
        raise ValueError(f"Unknown chart_type: {chart_type!r}")

    # Pass all optional kwargs through to the builder (granularity, metric, etc.)
    kwargs = {k: v for k, v in tool_input.items() if k not in ("chart_type",)}
    return builder(datasets, **kwargs)
```

> ⚠️ If `dispatch_chart_tool` already passes kwargs through, no change is needed here — just confirm `metric` isn't being dropped before the builder call.