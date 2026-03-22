"""
src/agents/analytics.py
-----------------------
Analytics Agent — data retrieval specialist.

Responsibilities:
  - Receives a specific data question from the Orchestrator
  - Calls data tools (from src/agents/tools.py) to fetch exact numbers
  - Returns a structured JSON string with the retrieved data
  - NEVER interprets or recommends — only fetches and returns facts

Anti-hallucination: system prompt explicitly forbids estimation.
If data is not available via tools, the agent must say so.
"""

from __future__ import annotations

import json
import os

import anthropic
import pandas as pd

from src.agents.tools import ANALYTICS_TOOLS
from src.agents.context import build_context_block
from src import metrics as m

MODEL = "claude-sonnet-4-6"
MAX_TOOL_ITERATIONS = 8

# ---------------------------------------------------------------------------
# Tool dispatcher — maps tool names to metrics functions
# ---------------------------------------------------------------------------

def _dispatch_tool(
    tool_name: str,
    tool_input: dict,
    datasets: dict[str, pd.DataFrame],
) -> str:
    """
    Routes an Analytics Agent tool call to the appropriate metrics function.
    Returns a JSON-serialisable string.
    """
    df_sessions    = datasets.get("sessions",        pd.DataFrame())
    df_funnel      = datasets.get("funnel_steps",    pd.DataFrame())
    df_activations = datasets.get("activations",     pd.DataFrame())
    df_meals       = datasets.get("meal_selections", pd.DataFrame())
    df_discounts   = datasets.get("discounts",       pd.DataFrame())

    try:
        if tool_name == "get_kpi_summary":
            result = m.get_kpi_summary(df_sessions, df_funnel, df_activations, df_meals, df_discounts)

        elif tool_name == "get_funnel_ctr":
            channel = tool_input.get("channel")
            device  = tool_input.get("device")
            df = m.get_funnel_ctr(df_funnel, channel=channel, device=device, df_sessions=df_sessions)
            result = df.to_dict(orient="records")

        elif tool_name == "get_conversion_by_channel":
            df = m.get_conversion_by_channel(df_sessions, df_activations)
            result = df.to_dict(orient="records")

        elif tool_name == "get_conversion_by_device":
            df = m.get_conversion_by_device(df_sessions, df_activations)
            result = df.to_dict(orient="records")

        elif tool_name == "get_activation_value_breakdown":
            group_by = tool_input.get("group_by", "both")
            if group_by in ("plan", "both"):
                df_plan = m.get_activation_value_by_plan(df_activations)
                plan_data = df_plan.to_dict(orient="records")
            else:
                plan_data = []
            if group_by in ("activation_type", "both"):
                df_type = m.get_activation_value_by_type(df_activations)
                type_data = df_type.to_dict(orient="records")
            else:
                type_data = []
            result = {"by_plan": plan_data, "by_activation_type": type_data}

        elif tool_name == "get_discount_analysis":
            df = m.get_discount_effectiveness(df_activations, df_discounts)
            pct_discount = (
                df_activations["has_discount"].mean() * 100
                if "has_discount" in df_activations.columns else 0.0
            )
            avg_disc_pct = (
                df_activations.loc[
                    df_activations["has_discount"] == True, "discount_pct"
                ].mean()
                if "has_discount" in df_activations.columns and "discount_pct" in df_activations.columns
                else 0.0
            )
            result = {
                "pct_activations_with_discount": round(pct_discount, 2),
                "avg_discount_pct": round(avg_disc_pct, 2),
                "by_discount_code": df.to_dict(orient="records"),
            }

        elif tool_name == "get_meal_type_performance":
            plan_filter = tool_input.get("plan_filter")
            df_act_filtered = (
                df_activations[df_activations["plan_name"] == plan_filter]
                if plan_filter else df_activations
            )
            df = m.get_meal_type_adoption(df_meals, df_act_filtered)
            result = df.to_dict(orient="records")

        elif tool_name == "get_activation_trend":
            granularity = tool_input.get("granularity", "week")
            df = m.get_activation_trend(df_activations, granularity=granularity)
            result = df.to_dict(orient="records")

        else:
            result = {"error": f"Unknown tool: {tool_name}"}

    except NotImplementedError:
        result = {
            "error": (
                f"The underlying metric for '{tool_name}' has not been implemented yet. "
                "Tell the user this metric is not available."
            )
        }
    except Exception as e:
        result = {"error": f"Tool execution error: {str(e)}"}

    return json.dumps(result, default=str)


# ---------------------------------------------------------------------------
# Analytics Agent main function
# ---------------------------------------------------------------------------

def run_analytics_agent(
    question: str,
    datasets: dict[str, pd.DataFrame],
    status_container=None,
) -> str:
    """
    Runs the Analytics Agent for a single question.
    May call multiple tools in a loop to gather all required data.

    Args:
        question: The specific data question from the Orchestrator.
        datasets: Dict of DataFrames from data/loader.py.
        status_container: Optional st.status() context for UI feedback.

    Returns:
        A JSON-formatted string with all retrieved data, or an error message.
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

    system_prompt = build_context_block(datasets) + """
=== YOUR ROLE: ANALYTICS AGENT ===
You are a data retrieval specialist. Your only job is to call the available tools
to fetch exact numbers that answer the question.

Rules:
- NEVER invent or estimate any number.
- NEVER make qualitative judgements (good/bad/concerning).
- Call as many tools as needed to fully answer the question.
- Return your findings as a structured, factual summary with exact numbers.
- If a tool returns an error, report the error — do not substitute a guess.
- If the data is insufficient to answer, say so explicitly.
"""

    messages = [{"role": "user", "content": question}]

    for iteration in range(MAX_TOOL_ITERATIONS):
        response = client.messages.create(
            model=MODEL,
            system=system_prompt,
            messages=messages,
            tools=ANALYTICS_TOOLS,
            max_tokens=4096,
        )

        if response.stop_reason == "end_turn":
            # Extract text response
            text = " ".join(
                block.text for block in response.content
                if hasattr(block, "text")
            )
            return text

        if response.stop_reason == "tool_use":
            # Append assistant message with tool use blocks
            messages.append({
                "role": "assistant",
                "content": [
                    block.model_dump() for block in response.content
                ],
            })

            # Dispatch all tool calls and batch results into a single user message
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    if status_container:
                        status_container.write(
                            f"📊 Analytics → `{block.name}` "
                            + (f"({_format_inputs(block.input)})" if block.input else "")
                        )
                    result_str = _dispatch_tool(block.name, block.input, datasets)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })

            messages.append({"role": "user", "content": tool_results})

        else:
            # Unexpected stop reason
            break

    return "Analytics Agent: reached maximum tool iterations without a final answer."


def _format_inputs(inputs: dict) -> str:
    """Format tool inputs for display in status container."""
    if not inputs:
        return ""
    return ", ".join(f"{k}={v}" for k, v in inputs.items())
