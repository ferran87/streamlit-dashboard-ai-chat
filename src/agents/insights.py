"""
src/agents/insights.py
----------------------
Insights Agent — interpretation and validation specialist.

Responsibilities:
  - Receives analytics data (from the Analytics Agent) + the original user question
  - Calls validate_metric() for every metric it wants to qualify as good/bad
  - Generates grounded insights, flags anomalies, surfaces recommendations
  - ONLY interprets numbers it has been given — never invents data

Anti-hallucination layers:
  1. Receives only Analytics Agent output (no raw access to data)
  2. Must call validate_metric() before any qualitative claim
  3. Hardcoded benchmarks in context — cannot be changed via data
"""

from __future__ import annotations

import json
import os

import anthropic
import pandas as pd

from src.agents.tools import INSIGHTS_TOOLS
from src.agents.context import build_insights_context_block, validate_metric

MODEL = "claude-sonnet-4-6"
MAX_TOOL_ITERATIONS = 6


# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------

def _dispatch_insights_tool(tool_name: str, tool_input: dict) -> str:
    """Routes Insights Agent tool calls."""
    if tool_name == "validate_metric":
        result = validate_metric(
            metric_name=tool_input["metric_name"],
            value=tool_input["value"],
        )
        return json.dumps(result)
    return json.dumps({"error": f"Unknown tool: {tool_name}"})


# ---------------------------------------------------------------------------
# Insights Agent main function
# ---------------------------------------------------------------------------

def run_insights_agent(
    analytics_result: str,
    original_question: str,
    datasets: dict[str, pd.DataFrame],
    status_container=None,
) -> str:
    """
    Runs the Insights Agent to interpret analytics data.

    Args:
        analytics_result: Factual data string returned by the Analytics Agent.
        original_question: The user's original question (for context).
        datasets: Dict of DataFrames (used only to build the context block).
        status_container: Optional st.status() context for UI feedback.

    Returns:
        A string with grounded insights and recommendations.
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

    system_prompt = build_insights_context_block(datasets) + """
=== YOUR ROLE: INSIGHTS AGENT ===
You are a funnel optimisation strategist at HelloFresh.
You have been given factual analytics data (retrieved by the Analytics Agent).
Your job is to interpret it and generate actionable insights.

Rules:
- ONLY interpret the numbers given to you in the user message below.
- NEVER invent additional data points not present in the analytics result.
- ALWAYS call validate_metric() before describing any metric as good, bad,
  healthy, concerning, or excellent. Use the tool's 'status' field in your response.
- Reference the specific number in every claim (e.g. "our CVR of 3.2% is...").
- Provide 2–4 concrete, prioritised recommendations based on the data.
- Keep your response clear and concise — suitable for a business audience.
- If the analytics result contains an error or insufficient data, say so clearly.
"""

    user_message = f"""Original question: {original_question}

Analytics data retrieved:
{analytics_result}

Please interpret this data and provide insights."""

    messages = [{"role": "user", "content": user_message}]

    for iteration in range(MAX_TOOL_ITERATIONS):
        response = client.messages.create(
            model=MODEL,
            system=system_prompt,
            messages=messages,
            tools=INSIGHTS_TOOLS,
            max_tokens=4096,
        )

        if response.stop_reason == "end_turn":
            text = " ".join(
                block.text for block in response.content
                if hasattr(block, "text")
            )
            return text

        if response.stop_reason == "tool_use":
            messages.append({
                "role": "assistant",
                "content": [block.model_dump() for block in response.content],
            })

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    if status_container:
                        status_container.write(
                            f"✅ Insights → validating `{block.input.get('metric_name', '')}` "
                            f"({block.input.get('value', '')}%)"
                        )
                    result_str = _dispatch_insights_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })

            messages.append({"role": "user", "content": tool_results})

        else:
            break

    return "Insights Agent: reached maximum tool iterations without a final answer."
