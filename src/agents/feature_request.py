"""AI agent that converts a user feature request into a structured PRD + code suggestion."""

from __future__ import annotations

from src.agents.unified import _get_client, MODEL

# ---------------------------------------------------------------------------
# Codebase context injected into the system prompt
# ---------------------------------------------------------------------------

_CODEBASE_CONTEXT = """
=== PROJECT: HelloFresh-style Funnel Analytics Dashboard ===
Stack: Python, Streamlit, Pandas, Plotly, Anthropic claude-sonnet-4-6 (tool calling + streaming)

--- DATA MODEL (Parquet files in data/) ---
sessions         ~50k rows  | session_id, session_date, channel, device, activated (bool)
funnel_steps    ~126k rows  | session_id, step_name (landing/menu_browse/plan_selection/delivery_settings/account_creation/payment/confirmation)
activations       ~5k rows  | activation_id, session_id, activation_date, plan_name, activation_type, activation_value, has_discount, discount_pct, discount_code
meal_selections   ~5k rows  | activation_id, meal_type (classic/veggie/protein/low_cal/quick/family), quantity
discounts           10 rows | discount_code, discount_pct

--- EXISTING METRIC FUNCTIONS (src/metrics.py) ---
get_kpi_summary(df_sessions, df_activations, df_funnel) → dict (15 KPIs)
get_funnel_ctr(df_sessions, df_funnel, channel=None, device=None) → DataFrame [step, sessions_reached, ctr_to_next, exit_rate]
get_conversion_by_channel(df_sessions) → DataFrame [channel, sessions, activations, cvr]
get_conversion_by_device(df_sessions) → DataFrame [device, sessions, activations, cvr]
get_activation_value_by_plan(df_activations) → DataFrame [plan_name, count, avg_value, total_value]
get_activation_value_by_type(df_activations) → DataFrame [activation_type, count, avg_value, discount_rate]
get_discount_effectiveness(df_activations, df_discounts) → DataFrame [discount_code, used_count, avg_value_with, avg_value_without, uplift_pct]
get_meal_type_adoption(df_activations, df_meals, plan_filter=None) → DataFrame [meal_type, activation_count, pct_of_activations]
get_activation_trend(df_activations, granularity="week") → DataFrame [period, activations, avg_value, total_revenue]
get_session_volume_trend(df_sessions, df_activations) → DataFrame [week, sessions, activated_sessions, cvr]
get_overall_conversion_rate(df_sessions) → float
get_funnel_drop_off(df_sessions, df_funnel) → DataFrame [step, dropped_sessions, drop_pct]

--- EXISTING AI TOOLS (src/agents/tools.py) ---
ANALYTICS_TOOLS (8 tools, all support date_range_start/date_range_end):
  get_kpi_summary, get_funnel_ctr, get_conversion_by_channel, get_conversion_by_device,
  get_activation_value_breakdown, get_discount_analysis, get_meal_type_performance, get_activation_trend

INSIGHTS_TOOLS (1 tool):
  validate_metric(metric_name, value, n=None) → benchmark status + confidence tier

GENERATE_CHART_TOOL (1 tool, 10 chart types):
  funnel_steps_bar, funnel_drop_off_waterfall, activation_trend_line, activation_type_pie,
  cvr_by_channel_bar, cvr_by_device_bar, activation_value_by_plan, meal_type_adoption_bar,
  discount_effectiveness, session_volume_trend

--- HOW THE AGENT WORKS (src/agents/unified.py) ---
1. Tool-call loop: Claude calls tools, results dispatched, loop continues until end_turn
2. _dispatch_analytics_tool(tool_name, tool_input, datasets): routes tool_name → metrics.py function
3. dispatch_chart_tool(tool_input, datasets): routes chart_type → charts.py builder via _CHART_REGISTRY dict
4. _apply_date_filter(datasets, date_start, date_end): FK cascade pre-filter before dispatch
5. Streaming synthesis: final Claude call (no tools) streams text to UI

--- HOW TO ADD A NEW ANALYTICS TOOL ---
Step 1 — src/metrics.py: Add a new function following the pattern above.
Step 2 — src/agents/tools.py: Add a new entry to ANALYTICS_TOOLS list with name, description, input_schema.
           Include **_DATE_PROPS in properties to get date filtering for free.
           Add to UNIFIED_TOOLS (already done automatically via ANALYTICS_TOOLS + INSIGHTS_TOOLS + [GENERATE_CHART_TOOL]).
Step 3 — src/agents/unified.py: Add an elif branch in _dispatch_analytics_tool() for the new tool_name.
           Call the new metrics function with the appropriate DataFrames from datasets.

--- HOW TO ADD A NEW CHART TYPE ---
Step 1 — src/charts.py: Add a new builder function build_xxx(datasets, **kw) → go.Figure.
Step 2 — src/agents/tools.py: Add the new chart type string to GENERATE_CHART_TOOL enum list.
Step 3 — src/agents/unified.py: Register the builder in _CHART_REGISTRY dict.
"""

_SYSTEM_PROMPT = f"""\
You are a senior product manager and software engineer working on a Streamlit analytics dashboard.
A user has submitted a feature request for functionality the current AI Chat cannot provide.

Your job is to output a structured document with two parts:
1. A Product Requirements Spec (PRD)
2. A concrete code suggestion using the actual project files

{_CODEBASE_CONTEXT}

--- OUTPUT FORMAT (use exactly this structure) ---

## 📋 Product Requirements Spec

### Problem
[1-2 sentences describing the gap the user hit]

### User Story
As a dashboard user, I want to [specific action] so that [business benefit].

### Proposed Solution
[2-3 sentences describing the feature at a product level]

### Success Criteria
- The AI Chat can answer: "[exact example question the user asked]"
- [1-2 additional measurable outcomes]

---

## 🛠️ Code Suggestion

### Files to Modify
| File | Change |
|---|---|
| [file] | [what changes] |

### Step-by-step Implementation

[For each file: show the function name, its signature, and the full implementation code.
Reference existing functions from the project wherever possible.
Code must be syntactically correct Python and follow the patterns described in the codebase context.]

---

Rules:
- Never invent DataFrame columns that don't exist in the data model above.
- Always follow the 3-step pattern (metrics.py → tools.py → unified.py) for new analytics tools.
- Keep code snippets complete and runnable — no pseudo-code.
- If the request cannot be implemented with the current data model, say so clearly and suggest what data would be needed.
"""


def generate_feature_request(description: str) -> str:
    """
    Takes a plain-text feature request description and returns a structured
    markdown string containing a PRD and code suggestion.

    Args:
        description: The user's free-text description of the feature they want.

    Returns:
        Markdown string with PRD + code suggestion sections.
    """
    client = _get_client()
    message = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Here is the feature request:\n\n{description}\n\n"
                    "Please generate the PRD and code suggestion."
                ),
            }
        ],
    )
    return message.content[0].text
