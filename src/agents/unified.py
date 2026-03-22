"""Unified Analytics Agent — single multi-tool exchange with streaming synthesis."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Generator

import anthropic
import pandas as pd

from src.agents.tools import UNIFIED_TOOLS
from src.agents.context import build_context_block, format_benchmark_table, validate_metric
from src import metrics as m
from src import charts
import plotly.graph_objects as go

MODEL = "claude-sonnet-4-6"
MAX_TOOL_ITERATIONS = 12

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    return _client


_BENCHMARK_TABLE: str = format_benchmark_table()

_ROLE_PROMPT: str = """
=== YOUR ROLE: ANALYTICS ASSISTANT ===
You are the AI Analytics Assistant for the HelloFresh Funnel Analytics Dashboard.
You have direct access to all data and visualisation tools.

CAPABILITIES:
- Data retrieval: call get_kpi_summary, get_funnel_ctr, get_conversion_by_channel,
  get_conversion_by_device, get_activation_value_breakdown, get_discount_analysis,
  get_meal_type_performance, get_activation_trend to fetch exact numbers from live data.
- Benchmark validation: call validate_metric BEFORE describing any metric as
  good, bad, healthy, concerning, or excellent. Never invent benchmark ranges.
- Chart generation: call generate_chart when a visual would communicate the answer
  better than numbers in text (comparisons, trends, rankings). The chart will appear
  ABOVE your text response. Call generate_chart at most once per turn.

RULES:
1. NEVER invent or estimate any metric value.
2. If a number is not in the LIVE DATA CONTEXT above, call the appropriate tool.
3. Always cite the exact figure (from context or tool result) in every quantitative claim.
4. Always call validate_metric before any qualitative assessment of a metric.
5. Keep final answers concise (3–4 paragraphs) and actionable.
6. If a tool returns an error or "unavailable", say so — never substitute a guess.

CONFIDENCE PROTOCOL — MANDATORY:
Determine the confidence tier for every quantitative claim from three factors:

FACTOR 1 — BENCHMARK: validate_metric returned healthy/warning/critical/excellent → benchmark exists.
  Returned no_benchmark → no benchmark exists for this metric.
FACTOR 2 — SAMPLE SIZE: Read from sessions_reached (funnel), sessions/activations (channel/device),
  used_count (discount), activation_count (meal type) already present in tool results.
  n < 30 → very_low | n 30–99 → low | n 100–499 → moderate | n ≥ 500 → high
  Top-level aggregates from get_kpi_summary or the LIVE CONTEXT block → treat as high.
FACTOR 3 — METRIC TYPE: Direct top-level aggregate → high. Derived (WoW growth, cross-segment,
  per-discount-code, per-meal-type %) → confidence is determined by Factor 2 sample size.

LANGUAGE BY CONFIDENCE TIER:
  HIGH (benchmark exists AND n ≥ 500 or top-level aggregate):
    Use definitive language: "The data shows...", "Our CVR is X%, within the healthy range of..."
  MEDIUM (benchmark exists but n 100–499, OR no_benchmark but n ≥ 500):
    Use hedging language: "The data suggests...", "This indicates...", "Appears to..."
  LOW (n 30–99, regardless of benchmark):
    Must state the sample size explicitly: "Based on only N sessions, this metric appears
    to... — treat as indicative only."
  VERY LOW (n < 30):
    Report raw number only. Explicitly decline to interpret:
    "Only N observations — too small for reliable conclusions."

WHEN validate_metric RETURNS status="no_benchmark":
  - State the raw number exactly as returned by the tool.
  - Say explicitly: "No benchmark exists for this metric."
  - DO NOT use these words without a validated healthy/warning/critical/excellent status:
    excellent, strong, healthy, poor, concerning, encouraging, worrying, impressive, disappointing,
    good performance, bad performance.
  - You MAY describe direction ("up 3 percentage points from last week") but NOT quality.
  - Example: "Week-on-week activation growth is +8.3%. No benchmark exists for this metric,
    so I cannot characterise whether this rate is high or low for HelloFresh."
  - If validate_metric also returns a sample_caveat: include that caveat verbatim.
"""


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

@dataclass
class TurnOutput:
    """Return value of run_turn(). Caller streams text and renders charts."""
    stream_gen: Generator
    charts: list
    chart_type_ids: list


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_turn(
    messages: list[dict],
    datasets: dict[str, pd.DataFrame],
    max_history: int = 20,
    status_container=None,
) -> TurnOutput:
    """Run one agentic turn: tool-call loop then streaming synthesis."""
    client = _get_client()

    # Build system prompt (context block is cached — cheap after first call)
    system_prompt = build_context_block(datasets) + _BENCHMARK_TABLE + _ROLE_PROMPT

    # Prepare API message list: flatten history, prune to max_history
    api_messages = _flatten_and_prune(messages, max_history)

    collected_charts: list[go.Figure] = []
    chart_type_ids: list[str] = []

    # -----------------------------------------------------------------------
    # Phase 1: Synchronous tool-call loop
    # -----------------------------------------------------------------------
    for iteration in range(MAX_TOOL_ITERATIONS):
        response = client.messages.create(
            model=MODEL,
            system=system_prompt,
            messages=api_messages,
            tools=UNIFIED_TOOLS,
            max_tokens=4096,
        )

        if response.stop_reason == "end_turn":
            # No tool calls — agent answered directly from context
            # Still stream for consistent UX (typewriter effect)
            final_text_blocks = [b.text for b in response.content if hasattr(b, "text")]
            direct_text = " ".join(final_text_blocks)
            return TurnOutput(
                stream_gen=_fake_stream(direct_text),
                charts=collected_charts,
                chart_type_ids=chart_type_ids,
            )

        if response.stop_reason == "tool_use":
            # Append assistant message (with tool_use blocks)
            api_messages.append({
                "role": "assistant",
                "content": [b.model_dump() for b in response.content],
            })

            # Dispatch all tool calls for this iteration
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                if status_container:
                    _log_tool_call(status_container, block.name, block.input)

                if block.name == "generate_chart":
                    fig = dispatch_chart_tool(block.input, datasets)
                    if fig is not None:
                        collected_charts.append(fig)
                        chart_type_ids.append(block.input.get("chart_type", "chart"))
                        result_json = json.dumps({"status": "ok", "chart_type": block.input.get("chart_type")})
                    else:
                        result_json = json.dumps({
                            "status": "unavailable",
                            "reason": "Chart data not available — metric may not be implemented yet.",
                        })

                elif block.name == "validate_metric":
                    n_raw = block.input.get("n")
                    result = validate_metric(
                        metric_name=block.input.get("metric_name", ""),
                        value=float(block.input.get("value", 0)),
                        n=int(n_raw) if n_raw is not None else None,
                    )
                    result_json = json.dumps(result)

                else:
                    result_json = _dispatch_analytics_tool(block.name, block.input, datasets)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_json,
                })

            # Batch all tool results into a single user message
            api_messages.append({"role": "user", "content": tool_results})

        else:
            # Unexpected stop reason (e.g. max_tokens) — break and stream what we have
            break

    # -----------------------------------------------------------------------
    # Phase 2: Streaming synthesis call (no tools — forces text-only response)
    # -----------------------------------------------------------------------
    # api_messages now contains the full tool exchange. Issue a streaming call
    # so the user sees tokens as they arrive (~2s to first token vs 8-20s buffered).
    stream_gen = _make_stream_generator(client, system_prompt, api_messages)

    return TurnOutput(
        stream_gen=stream_gen,
        charts=collected_charts,
        chart_type_ids=chart_type_ids,
    )


# ---------------------------------------------------------------------------
# Chart tool dispatcher — dict-based registry
# ---------------------------------------------------------------------------

def _chart_funnel_steps(ds, **kw):
    return charts.funnel_steps_bar(m.get_funnel_ctr(
        ds["funnel_steps"], channel=kw.get("channel"), device=kw.get("device"),
        df_sessions=ds["sessions"]))

def _chart_activation_type_pie(ds, **kw):
    df = m.get_activation_value_by_type(ds["activations"])
    return charts.activation_type_pie(df[["activation_type", "count"]].copy())

_CHART_REGISTRY: dict[str, callable] = {
    "funnel_steps_bar":           _chart_funnel_steps,
    "funnel_drop_off_waterfall":  lambda ds, **kw: charts.funnel_drop_off_waterfall(m.get_funnel_drop_off(ds["funnel_steps"])),
    "activation_trend_line":      lambda ds, **kw: charts.activation_trend_line(m.get_activation_trend(ds["activations"], granularity=kw.get("granularity", "week"))),
    "activation_type_pie":        _chart_activation_type_pie,
    "cvr_by_channel_bar":         lambda ds, **kw: charts.cvr_by_channel_bar(m.get_conversion_by_channel(ds["sessions"], ds["activations"])),
    "cvr_by_device_bar":          lambda ds, **kw: charts.cvr_by_device_bar(m.get_conversion_by_device(ds["sessions"], ds["activations"])),
    "activation_value_by_plan":   lambda ds, **kw: charts.activation_value_by_plan_bar(m.get_activation_value_by_plan(ds["activations"])),
    "meal_type_adoption_bar":     lambda ds, **kw: charts.meal_type_adoption_bar(m.get_meal_type_adoption(ds["meal_selections"], ds["activations"])),
    "discount_effectiveness":     lambda ds, **kw: charts.discount_effectiveness_table(m.get_discount_effectiveness(ds["activations"], ds["discounts"])),
    "session_volume_trend":       lambda ds, **kw: charts.session_volume_trend(m.get_session_volume_trend(ds["sessions"])),
}


def dispatch_chart_tool(tool_input: dict, datasets: dict[str, pd.DataFrame]) -> go.Figure | None:
    """Build a chart from tool_input. Returns None on any error (graceful degradation)."""
    chart_type = tool_input.get("chart_type", "")
    builder = _CHART_REGISTRY.get(chart_type)
    if builder is None:
        return None
    try:
        return builder(datasets, **tool_input)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Analytics tool dispatcher
# ---------------------------------------------------------------------------

def _dispatch_analytics_tool(
    tool_name: str,
    tool_input: dict,
    datasets: dict[str, pd.DataFrame],
) -> str:
    """Routes analytics tool calls to metrics functions. Returns JSON string."""
    df_sessions    = datasets.get("sessions",        pd.DataFrame())
    df_funnel      = datasets.get("funnel_steps",    pd.DataFrame())
    df_activations = datasets.get("activations",     pd.DataFrame())
    df_meals       = datasets.get("meal_selections", pd.DataFrame())
    df_discounts   = datasets.get("discounts",       pd.DataFrame())

    try:
        if tool_name == "get_kpi_summary":
            result = m.get_kpi_summary(df_sessions, df_funnel, df_activations,
                                       df_meals, df_discounts)

        elif tool_name == "get_funnel_ctr":
            df = m.get_funnel_ctr(
                df_funnel,
                channel=tool_input.get("channel"),
                device=tool_input.get("device"),
                df_sessions=df_sessions,
            )
            result = df.to_dict(orient="records")

        elif tool_name == "get_conversion_by_channel":
            df = m.get_conversion_by_channel(df_sessions, df_activations)
            result = df.to_dict(orient="records")

        elif tool_name == "get_conversion_by_device":
            df = m.get_conversion_by_device(df_sessions, df_activations)
            result = df.to_dict(orient="records")

        elif tool_name == "get_activation_value_breakdown":
            group_by = tool_input.get("group_by", "both")
            plan_data = (
                m.get_activation_value_by_plan(df_activations).to_dict(orient="records")
                if group_by in ("plan", "both") else []
            )
            type_data = (
                m.get_activation_value_by_type(df_activations).to_dict(orient="records")
                if group_by in ("activation_type", "both") else []
            )
            result = {"by_plan": plan_data, "by_activation_type": type_data}

        elif tool_name == "get_discount_analysis":
            df = m.get_discount_effectiveness(df_activations, df_discounts)
            pct = (df_activations["has_discount"].mean() * 100
                   if "has_discount" in df_activations.columns else 0.0)
            avg_d = (
                df_activations.loc[df_activations["has_discount"], "discount_pct"].mean()
                if "has_discount" in df_activations.columns
                   and "discount_pct" in df_activations.columns
                else 0.0
            )
            result = {
                "pct_activations_with_discount": round(float(pct), 2),
                "avg_discount_pct": round(float(avg_d), 2),
                "by_discount_code": df.to_dict(orient="records"),
            }

        elif tool_name == "get_meal_type_performance":
            plan_f = tool_input.get("plan_filter")
            df_act = (df_activations[df_activations["plan_name"] == plan_f]
                      if plan_f else df_activations)
            df = m.get_meal_type_adoption(df_meals, df_act)
            result = df.to_dict(orient="records")

        elif tool_name == "get_activation_trend":
            df = m.get_activation_trend(
                df_activations, granularity=tool_input.get("granularity", "week")
            )
            result = df.to_dict(orient="records")

        else:
            result = {"error": f"Unknown tool: {tool_name}"}

    except NotImplementedError:
        result = {
            "error": (
                f"The metric for '{tool_name}' is not implemented yet. "
                "Tell the user this specific data is not available."
            )
        }
    except Exception as e:
        result = {"error": f"Tool error: {str(e)}"}

    return json.dumps(result, default=str)


# ---------------------------------------------------------------------------
# Streaming helpers
# ---------------------------------------------------------------------------

def _make_stream_generator(
    client: anthropic.Anthropic,
    system_prompt: str,
    messages: list[dict],
) -> Generator[str, None, None]:
    """Yield text chunks from a streaming API call (no tools)."""
    with client.messages.stream(
        model=MODEL,
        system=system_prompt,
        messages=messages,
        max_tokens=4096,
        # No tools — model cannot make further tool calls; yields text only
    ) as stream:
        for chunk in stream.text_stream:
            yield chunk


def _fake_stream(text: str) -> Generator[str, None, None]:
    """Yield pre-computed text as a single chunk for consistent st.write_stream() UX."""
    yield text


# ---------------------------------------------------------------------------
# History helpers
# ---------------------------------------------------------------------------

def _flatten_and_prune(messages: list[dict], max_history: int) -> list[dict]:
    """Convert session messages to API format, prune to last max_history, start on user turn."""
    result = []
    for msg in messages:
        role = msg.get("role")
        if role not in ("user", "assistant"):
            continue
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                b.get("text", "") for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            ).strip()
        if content:
            result.append({"role": role, "content": content})

    # Prune to max_history
    if len(result) > max_history:
        result = result[-max_history:]

    # Never start with an assistant turn
    while result and result[0]["role"] != "user":
        result.pop(0)

    return result


# ---------------------------------------------------------------------------
# Status container helpers
# ---------------------------------------------------------------------------

def _log_tool_call(status_container, tool_name: str, tool_input: dict) -> None:
    """Write a tool call trace line to the st.status() container."""
    icons = {
        "generate_chart":              "📊",
        "validate_metric":             "✅",
        "get_kpi_summary":             "🔢",
        "get_funnel_ctr":              "🔍",
        "get_conversion_by_channel":   "📡",
        "get_conversion_by_device":    "📱",
        "get_activation_value_breakdown": "💰",
        "get_discount_analysis":       "🏷️",
        "get_meal_type_performance":   "🥗",
        "get_activation_trend":        "📈",
    }
    icon = icons.get(tool_name, "🔧")
    params = ""
    if tool_input:
        params = " · " + ", ".join(f"{k}={v}" for k, v in tool_input.items()
                                    if v is not None)
    status_container.write(f"{icon} `{tool_name}`{params}")
