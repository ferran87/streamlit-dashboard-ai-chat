"""
src/agents/orchestrator.py
--------------------------
Orchestrator Agent — routes, delegates, and synthesises.

Responsibilities:
  - Receives the user's question
  - Decides whether to answer from injected context (simple KPI lookups)
    or delegate to sub-agents
  - Calls the Analytics Agent to fetch exact numbers
  - Calls the Insights Agent to interpret those numbers
  - Synthesises a final, grounded response for the user

The Orchestrator is the only agent whose message history persists across
user turns (stored in st.session_state.messages).
Sub-agent calls use fresh, isolated message lists per turn.

Agent flow:
  User question
    ├─ Simple KPI → answer from injected context directly
    └─ Complex / multi-step
         ├─ Analytics Agent → exact numbers (tools: 8 data-query tools)
         ├─ Insights Agent → interpretation (tools: validate_metric)
         └─ Synthesise → final response to user
"""

from __future__ import annotations

import json
import os

import anthropic
import pandas as pd

from src.agents.analytics import run_analytics_agent
from src.agents.insights import run_insights_agent
from src.agents.context import build_context_block

MODEL = "claude-sonnet-4-6"
MAX_ORCHESTRATOR_ITERATIONS = 6

# ---------------------------------------------------------------------------
# Orchestrator tools (internal — not exposed to the user)
# ---------------------------------------------------------------------------

ORCHESTRATOR_TOOLS: list[dict] = [
    {
        "name": "delegate_to_analytics",
        "description": (
            "Delegate a data retrieval task to the Analytics Agent. "
            "The Analytics Agent will call data tools and return exact numbers. "
            "Use this when the question requires specific metrics, filtered data, "
            "or historical trends that may not be in the injected context. "
            "Provide a precise, self-contained question for the Analytics Agent."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": (
                        "The precise data question for the Analytics Agent. "
                        "Be specific: include any filters (channel, device, time period) "
                        "and exactly what metrics you need returned."
                    ),
                },
            },
            "required": ["question"],
        },
    },
    {
        "name": "delegate_to_insights",
        "description": (
            "Delegate an interpretation task to the Insights Agent. "
            "The Insights Agent will validate metrics against benchmarks and "
            "generate grounded recommendations. "
            "ALWAYS pass the analytics result from a previous delegate_to_analytics call. "
            "Never call this without analytics data to interpret."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "analytics_result": {
                    "type": "string",
                    "description": (
                        "The factual data returned by the Analytics Agent. "
                        "Pass the full text — do not summarise or edit it."
                    ),
                },
                "original_question": {
                    "type": "string",
                    "description": "The user's original question, for context.",
                },
            },
            "required": ["analytics_result", "original_question"],
        },
    },
]


# ---------------------------------------------------------------------------
# Orchestrator main function
# ---------------------------------------------------------------------------

def run_turn(
    messages: list[dict],
    datasets: dict[str, pd.DataFrame],
    status_container=None,
) -> tuple[str, list[dict]]:
    """
    Runs one full agentic turn of the Orchestrator.

    Args:
        messages: Full conversation history (from st.session_state.messages).
                  Only user/assistant text messages — tool messages from
                  sub-agents are NOT included here.
        datasets: Dict of DataFrames from data/loader.py.
        status_container: Optional st.status() context for UI feedback.

    Returns:
        (final_response_text, updated_messages_list)
        The updated messages list should replace st.session_state.messages.
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

    system_prompt = build_context_block(datasets) + """
=== YOUR ROLE: ORCHESTRATOR ===
You are the main AI assistant for the HelloFresh Funnel Analytics Dashboard.
You answer questions about funnel performance, conversion rates, activations,
discounts, meal types, and channel/device breakdowns.

Decision rules:
1. If the answer is clearly present in the LIVE DATA CONTEXT above, answer directly.
   Do NOT call sub-agents for simple current-KPI questions (e.g. "what is our CVR?").

2. For questions requiring specific metrics, historical trends, filtered data,
   or qualitative interpretation:
   a. Call delegate_to_analytics first to get exact numbers.
   b. Then call delegate_to_insights with those numbers for interpretation.
   c. Synthesise a clear, concise final answer for the user.

3. For complex questions requiring multiple data dimensions:
   a. You may call delegate_to_analytics multiple times with different questions.
   b. Collect all results before calling delegate_to_insights.

4. NEVER invent numbers. If you cannot answer from context or sub-agents, say so.
5. Always cite specific numbers in your final response.
6. Keep your final response focused and actionable — no more than 3–4 paragraphs.
"""

    # Build Orchestrator message list — only user/assistant text turns
    orch_messages = _filter_messages_for_orchestrator(messages)

    for iteration in range(MAX_ORCHESTRATOR_ITERATIONS):
        response = client.messages.create(
            model=MODEL,
            system=system_prompt,
            messages=orch_messages,
            tools=ORCHESTRATOR_TOOLS,
            max_tokens=4096,
        )

        if response.stop_reason == "end_turn":
            final_text = " ".join(
                block.text for block in response.content
                if hasattr(block, "text")
            )
            return final_text, messages  # return original messages unchanged

        if response.stop_reason == "tool_use":
            # Append orchestrator's assistant message (with tool use blocks)
            orch_messages.append({
                "role": "assistant",
                "content": [block.model_dump() for block in response.content],
            })

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                if block.name == "delegate_to_analytics":
                    question = block.input["question"]
                    if status_container:
                        status_container.write(f"🔍 Calling Analytics Agent: _{question}_")
                    result = run_analytics_agent(
                        question=question,
                        datasets=datasets,
                        status_container=status_container,
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

                elif block.name == "delegate_to_insights":
                    analytics_result   = block.input["analytics_result"]
                    original_question  = block.input["original_question"]
                    if status_container:
                        status_container.write("💡 Calling Insights Agent…")
                    result = run_insights_agent(
                        analytics_result=analytics_result,
                        original_question=original_question,
                        datasets=datasets,
                        status_container=status_container,
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

                else:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps({"error": f"Unknown tool: {block.name}"}),
                    })

            orch_messages.append({"role": "user", "content": tool_results})

        else:
            break

    return (
        "I was unable to complete this request within the allowed number of steps. "
        "Please try rephrasing your question.",
        messages,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _filter_messages_for_orchestrator(messages: list[dict]) -> list[dict]:
    """
    Extract only user/assistant text messages for the Orchestrator's conversation.
    Filters out any tool-result messages that may have been stored.
    Flattens list-content messages to plain text.
    """
    filtered = []
    for msg in messages:
        role = msg.get("role")
        if role not in ("user", "assistant"):
            continue

        content = msg.get("content", "")

        # Flatten list content to text
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    # Skip tool_use and tool_result blocks
                elif isinstance(block, str):
                    text_parts.append(block)
            content = " ".join(text_parts).strip()

        if content:
            filtered.append({"role": role, "content": content})

    return filtered
