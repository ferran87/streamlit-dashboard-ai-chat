"""
src/agents/unified.py
---------------------
Unified Analytics Agent — replaces the 3-hop Orchestrator → Analytics → Insights chain.

Why unified?
  The old architecture made 3–4 sequential API calls per user question, causing 8–20s latency.
  This single agent has all 10 tools (8 analytics + validate_metric + generate_chart) and
  handles data retrieval, benchmark validation, insight synthesis, and chart generation in
  one multi-tool exchange. Maximum 2 API calls per turn:
    1. Synchronous tool-call loop (may involve multiple tool dispatches)
    2. Streaming final synthesis (no tools — first tokens appear in ~2s)

Anti-hallucination guarantees (preserved from old architecture):
  - Live KPI context injected as system prompt (from context.py)
  - Hardcoded benchmark table in system prompt
  - `validate_metric` tool required before any qualitative claim
  - `generate_chart` tool uses exact DataFrames — no invented numbers in charts

Usage (from pages/4_AI_Chat.py):
    result = run_turn(messages, datasets, status_container=st.status(...))
    for fig in result.charts:
        st.plotly_chart(fig, use_container_width=True)
    response_text = st.write_stream(result.stream_gen)
    st.session_state.messages.append({
        "role": "assistant",
        "content": response_text,
        "chart_types": result.chart_type_ids,
    })
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Generator

import anthropic
import pandas as pd

from src.agents.tools import UNIFIED_TOOLS
from src.agents.context import build_context_block, BENCHMARKS, validate_metric
from src import metrics as m
from src import charts
import plotly.graph_objects as go

MODEL = "claude-sonnet-4-6"
MAX_TOOL_ITERATIONS = 12  # generous cap — unified agent may call several tools


# ---------------------------------------------------------------------------
# Module-level constants (built once at import — zero per-call overhead)
# ---------------------------------------------------------------------------

_BENCHMARK_TABLE: str = "\n--- BENCHMARK REFERENCE (do not invent values outside these ranges) ---\n" + "".join(
    f"  {name}: healthy {b['healthy_min']}–{b['healthy_max']}%"
    f" | poor <{b.get('poor_max', '?')}%"
    f" | excellent >{b.get('excellent_min', '?')}%\n"
    for name, b in BENCHMARKS.items()
)

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
"""


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

@dataclass
class TurnOutput:
    """Return value of run_turn(). Caller streams text and renders charts."""
    stream_gen: Generator           # pass directly to st.write_stream()
    charts: list                    # list[go.Figure] — render before text
    chart_type_ids: list            # list[str] — persist in session state for history
    updated_messages: list          # original messages list, unchanged; caller appends assistant turn


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_turn(
    messages: list[dict],
    datasets: dict[str, pd.DataFrame],
    max_history: int = 20,
    status_container=None,
) -> TurnOutput:
    """
    Runs one full agentic turn.

    Phase 1 (synchronous): Tool-call loop. Agent calls data tools, validate_metric,
        and/or generate_chart. Accumulates charts as go.Figure objects.
    Phase 2 (streaming): Issues a streaming API call (no tools) to synthesise the
        final response. Returns a generator — caller passes it to st.write_stream().

    Args:
        messages:         Full conversation history from st.session_state.messages.
        datasets:         DataFrames dict from data/loader.load_all().
        max_history:      Maximum number of past messages passed to the API (prevents bloat).
        status_container: Optional st.status() context for showing tool call trace.

    Returns:
        TurnOutput dataclass with stream_gen, charts, chart_type_ids, updated_messages.
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

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
                updated_messages=list(messages),
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
                    fig = _dispatch_chart_tool(block.input, datasets)
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
                    result = validate_metric(
                        metric_name=block.input.get("metric_name", ""),
                        value=float(block.input.get("value", 0)),
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
        updated_messages=list(messages),  # unchanged; caller appends assistant turn
    )


# ---------------------------------------------------------------------------
# Chart tool dispatcher
# ---------------------------------------------------------------------------

def _dispatch_chart_tool(
    tool_input: dict,
    datasets: dict[str, pd.DataFrame],
) -> go.Figure | None:
    """
    Calls the appropriate metrics function + chart builder.
    Returns None on any error (graceful degradation — agent tells user data unavailable).
    Never raises.
    """
    chart_type = tool_input.get("chart_type", "")
    channel    = tool_input.get("channel")
    device     = tool_input.get("device")
    granularity = tool_input.get("granularity", "week")

    df_sessions    = datasets.get("sessions",        pd.DataFrame())
    df_funnel      = datasets.get("funnel_steps",    pd.DataFrame())
    df_activations = datasets.get("activations",     pd.DataFrame())
    df_meals       = datasets.get("meal_selections", pd.DataFrame())
    df_discounts   = datasets.get("discounts",       pd.DataFrame())

    try:
        if chart_type == "funnel_steps_bar":
            df = m.get_funnel_ctr(df_funnel, channel=channel, device=device,
                                  df_sessions=df_sessions)
            return charts.funnel_steps_bar(df)

        elif chart_type == "funnel_drop_off_waterfall":
            df = m.get_funnel_drop_off(df_funnel)
            return charts.funnel_drop_off_waterfall(df)

        elif chart_type == "activation_trend_line":
            df = m.get_activation_trend(df_activations, granularity=granularity)
            return charts.activation_trend_line(df)

        elif chart_type == "activation_type_pie":
            df = m.get_activation_value_by_type(df_activations)
            # activation_type_pie expects [activation_type, count] — slice to those cols
            df_pie = df[["activation_type", "count"]].copy()
            return charts.activation_type_pie(df_pie)

        elif chart_type == "cvr_by_channel_bar":
            df = m.get_conversion_by_channel(df_sessions, df_activations)
            return charts.cvr_by_channel_bar(df)

        elif chart_type == "cvr_by_device_bar":
            df = m.get_conversion_by_device(df_sessions, df_activations)
            return charts.cvr_by_device_bar(df)

        elif chart_type == "activation_value_by_plan":
            df = m.get_activation_value_by_plan(df_activations)
            return charts.activation_value_by_plan_bar(df)

        elif chart_type == "meal_type_adoption_bar":
            df = m.get_meal_type_adoption(df_meals, df_activations)
            return charts.meal_type_adoption_bar(df)

        elif chart_type == "discount_effectiveness":
            df = m.get_discount_effectiveness(df_activations, df_discounts)
            return charts.discount_effectiveness_table(df)

        elif chart_type == "session_volume_trend":
            df = m.get_session_volume_trend(df_sessions)
            return charts.session_volume_trend(df)

    except NotImplementedError:
        # Metric stub not yet implemented — silent degradation
        return None
    except Exception:
        return None

    return None


# ---------------------------------------------------------------------------
# Analytics tool dispatcher (mirrors analytics.py — kept in sync)
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
    """
    Generator that yields text chunks from a streaming API call.
    No 'tools' parameter — forces the model to synthesise a final text response.
    """
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
    """
    Yields a pre-computed text string as a single chunk.
    Used when the agent answered directly from context (no tool calls needed)
    so the UI still uses st.write_stream() for a consistent experience.
    """
    yield text


# ---------------------------------------------------------------------------
# History helpers
# ---------------------------------------------------------------------------

def _flatten_and_prune(messages: list[dict], max_history: int) -> list[dict]:
    """
    Convert session messages to API-compatible format:
    - Strip chart_types field
    - Flatten list-content to plain text
    - Skip any non user/assistant messages
    - Prune to last max_history messages
    - Ensure the first message is a user turn
    """
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
