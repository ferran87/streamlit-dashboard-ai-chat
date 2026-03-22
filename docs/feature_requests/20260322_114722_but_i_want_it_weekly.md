## 📋 Product Requirements Spec

### Problem
The AI Chat can report weekly CVR trends in aggregate, but has no way to break that trend down by device type over time. When a user asks for a weekly CVR view segmented by device (e.g., "show me weekly CVR by device"), the agent falls back to a flat aggregate table and explicitly admits the chart capability doesn't exist.

### User Story
As a dashboard user, I want to see weekly conversion rate trends broken down by device type (mobile, desktop, tablet) on a single chart so that I can identify whether CVR shifts over time are driven by a specific device segment and prioritize product improvements accordingly.

### Proposed Solution
Add a new analytics tool `get_cvr_trend_by_device` that pivots session data by week and device, computing CVR for each cell. Pair it with a new `cvr_trend_by_device_line` chart type that renders a multi-line Plotly figure — one line per device — so the AI can answer any "weekly CVR by device" question with both a data table and a visualization.

### Success Criteria
- The AI Chat can answer: "Show me weekly CVR by device" and "I want it weekly" (as a follow-up to a device CVR question) by rendering a multi-line chart with one line per device.
- The new tool respects `date_range_start` / `date_range_end` filters, consistent with all existing analytics tools.
- The chart is registered in `_CHART_REGISTRY` and reachable via `GENERATE_CHART_TOOL` so Claude can call it independently.

---

## 🛠️ Code Suggestion

### Files to Modify
| File | Change |
|---|---|
| `src/metrics.py` | Add `get_cvr_trend_by_device()` function |
| `src/charts.py` | Add `build_cvr_trend_by_device_line()` chart builder |
| `src/agents/tools.py` | Add `get_cvr_trend_by_device` to `ANALYTICS_TOOLS`; add `cvr_trend_by_device_line` to `GENERATE_CHART_TOOL` enum |
| `src/agents/unified.py` | Add `elif` branch in `_dispatch_analytics_tool()`; register chart in `_CHART_REGISTRY` |

---

### Step-by-step Implementation

---

#### Step 1 — `src/metrics.py`

```python
def get_cvr_trend_by_device(
    df_sessions: pd.DataFrame,
    granularity: str = "week",
) -> pd.DataFrame:
    """
    Returns weekly (or daily/monthly) CVR broken down by device.

    Output columns: period, device, sessions, activations, cvr
    Wide-pivot columns are also returned for charting convenience:
      period | device | sessions | activations | cvr
    One row per (period, device) combination.
    """
    df = df_sessions.copy()
    df["session_date"] = pd.to_datetime(df["session_date"])

    # Build period column using the same granularity logic as get_activation_trend
    if granularity == "week":
        df["period"] = df["session_date"].dt.to_period("W").apply(
            lambda p: p.start_time
        )
    elif granularity == "month":
        df["period"] = df["session_date"].dt.to_period("M").apply(
            lambda p: p.start_time
        )
    else:  # day
        df["period"] = df["session_date"].dt.normalize()

    grouped = (
        df.groupby(["period", "device"])
        .agg(
            sessions=("session_id", "count"),
            activations=("activated", "sum"),
        )
        .reset_index()
    )
    grouped["cvr"] = (grouped["activations"] / grouped["sessions"] * 100).round(2)
    grouped["period"] = grouped["period"].astype(str)

    return grouped.sort_values(["period", "device"]).reset_index(drop=True)
```

---

#### Step 2 — `src/charts.py`

```python
def build_cvr_trend_by_device_line(datasets: dict, **kw) -> go.Figure:
    """
    Multi-line CVR trend chart, one line per device.

    Expected kw:
      granularity: "week" | "month" | "day"  (default "week")
    """
    from src.metrics import get_cvr_trend_by_device

    df_sessions = datasets["sessions"]
    granularity = kw.get("granularity", "week")

    df = get_cvr_trend_by_device(df_sessions, granularity=granularity)

    if df.empty:
        fig = go.Figure()
        fig.update_layout(title="No data available for selected filters.")
        return fig

    devices = sorted(df["device"].unique())

    # Consistent colour palette aligned with existing dashboard palette
    PALETTE = [
        "#FF6B35",  # HelloFresh orange
        "#2EC4B6",  # teal
        "#6A4C93",  # purple
        "#FFB400",  # amber
    ]

    fig = go.Figure()

    for i, device in enumerate(devices):
        device_df = df[df["device"] == device].sort_values("period")
        fig.add_trace(
            go.Scatter(
                x=device_df["period"],
                y=device_df["cvr"],
                mode="lines+markers",
                name=device.capitalize(),
                line=dict(color=PALETTE[i % len(PALETTE)], width=2),
                marker=dict(size=6),
                hovertemplate=(
                    f"<b>{device.capitalize()}</b><br>"
                    "Period: %{x}<br>"
                    "CVR: %{y:.2f}%<br>"
                    "Sessions: %{customdata[0]:,}<br>"
                    "Activations: %{customdata[1]:,}<extra></extra>"
                ),
                customdata=device_df[["sessions", "activations"]].values,
            )
        )

    period_label = granularity.capitalize()
    fig.update_layout(
        title=dict(
            text=f"Conversion Rate by Device — {period_label}ly Trend",
            font=dict(size=18),
        ),
        xaxis=dict(
            title=period_label,
            tickangle=-30,
            showgrid=False,
        ),
        yaxis=dict(
            title="Conversion Rate (%)",
            ticksuffix="%",
            showgrid=True,
            gridcolor="rgba(200,200,200,0.3)",
        ),
        legend=dict(
            title="Device",
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=60, r=30, t=80, b=60),
    )

    return fig
```

---

#### Step 3 — `src/agents/tools.py`

**3a. Add the new analytics tool to `ANALYTICS_TOOLS`:**

```python
# Add this entry to the ANALYTICS_TOOLS list
{
    "name": "get_cvr_trend_by_device",
    "description": (
        "Returns conversion rate (CVR) trend broken down by device type (mobile, desktop, tablet) "
        "over time. Use this when the user asks for weekly, monthly, or daily CVR by device, "
        "or asks to see how CVR differs across devices over a time period. "
        "Complements get_session_volume_trend (which is aggregate-only) and "
        "get_conversion_by_device (which has no time dimension)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "granularity": {
                "type": "string",
                "enum": ["day", "week", "month"],
                "description": "Time granularity for grouping. Default is 'week'.",
            },
            **_DATE_PROPS,  # Injects date_range_start / date_range_end for free
        },
        "required": [],
    },
},
```

**3b. Add `cvr_trend_by_device_line` to the `GENERATE_CHART_TOOL` enum:**

```python
# Inside GENERATE_CHART_TOOL, locate the "chart_type" enum list and append:
"cvr_trend_by_device_line",

# The full chart_type property should look like this (showing only the modified enum):
"chart_type": {
    "type": "string",
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
        "cvr_trend_by_device_line",   # ← NEW
    ],
    "description": "The type of chart to generate.",
},
```

---

#### Step 4 — `src/agents/unified.py`

**4a. Add the `elif` branch in `_dispatch_analytics_tool()`:**

```python
elif tool_name == "get_cvr_trend_by_device":
    from src.metrics import get_cvr_trend_by_device

    granularity = tool_input.get("granularity", "week")
    result_df = get_cvr_trend_by_device(
        datasets["sessions"],
        granularity=granularity,
    )
    return result_df.to_dict(orient="records")
```

**4b. Register the new chart builder in `_CHART_REGISTRY`:**

```python
# Inside the _CHART_REGISTRY dict, add:
"cvr_trend_by_device_line": build_cvr_trend_by_device_line,
```

Make sure the import is present at the top of `unified.py` (or wherever `_CHART_REGISTRY` is defined):

```python
from src.charts import (
    # ... existing imports ...
    build_cvr_trend_by_device_line,   # ← NEW
)
```

---

### How the full conversation flow works after this change

```
User:  "Show me weekly CVR by device"
         │
         ▼
Claude calls get_cvr_trend_by_device(granularity="week")
         │
         ▼  _dispatch_analytics_tool → metrics.get_cvr_trend_by_device()
         │  returns list of {period, device, sessions, activations, cvr} records
         │
Claude calls generate_chart(chart_type="cvr_trend_by_device_line", granularity="week")
         │
         ▼  dispatch_chart_tool → _CHART_REGISTRY → build_cvr_trend_by_device_line()
         │  returns go.Figure (multi-line, one line per device)
         │
Claude streams synthesis text:
  "Here's the weekly CVR trend by device. Desktop leads at ~11.2%
   most weeks, while mobile shows a dip in the week of Jan 12..."
```