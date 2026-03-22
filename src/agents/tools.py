"""
src/agents/tools.py
-------------------
Anthropic tool schemas for the Analytics Agent.
Each tool maps to a function in src/metrics.py.

ANALYTICS_TOOLS  — used by the Analytics Agent (8 data-query tools)
INSIGHTS_TOOLS   — used by the Insights Agent (1 validation tool)
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Analytics Agent tools
# ---------------------------------------------------------------------------

ANALYTICS_TOOLS: list[dict] = [
    {
        "name": "get_kpi_summary",
        "description": (
            "Returns all current top-level KPIs as a flat JSON object: "
            "total_sessions, total_activations, overall_cvr (%), avg_activation_value ($), "
            "total_revenue ($), top_channel, top_channel_cvr (%), "
            "worst_funnel_step, worst_funnel_ctr (%), best_funnel_step, best_funnel_ctr (%), "
            "pct_with_discount (%), avg_discount_pct (%), date_min, date_max. "
            "Use this for overall health questions or when you need current top-line numbers."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_funnel_ctr",
        "description": (
            "Returns click-through rate (CTR) for each funnel step, plus sessions reached "
            "and exit rate at each step. "
            "Optionally filter by channel (organic_search, paid_search, paid_social, email, "
            "referral, direct) and/or device (mobile, desktop, tablet). "
            "Use this for questions about funnel performance, drop-off, step-level conversion, "
            "or where users are abandoning."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Filter by acquisition channel. Omit for all channels.",
                    "enum": ["organic_search", "paid_search", "paid_social",
                             "email", "referral", "direct"],
                },
                "device": {
                    "type": "string",
                    "description": "Filter by device type. Omit for all devices.",
                    "enum": ["mobile", "desktop", "tablet"],
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_conversion_by_channel",
        "description": (
            "Returns session count, activation count, and CVR (%) for each acquisition channel. "
            "Use for questions about which channel performs best, channel comparison, "
            "or paid vs organic conversion."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_conversion_by_device",
        "description": (
            "Returns session count, activation count, and CVR (%) broken down by device type "
            "(mobile, desktop, tablet). "
            "Use for questions about mobile vs desktop conversion, device performance, "
            "or mobile optimisation opportunities."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_activation_value_breakdown",
        "description": (
            "Returns activation count, average value, and total revenue broken down by "
            "plan name AND by activation type (first_order, reactivation, referral, gift). "
            "Use for questions about revenue by plan, which plan is most valuable, "
            "reactivation revenue, or basket size by plan."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "group_by": {
                    "type": "string",
                    "description": "Dimension to group by.",
                    "enum": ["plan", "activation_type", "both"],
                    "default": "both",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_discount_analysis",
        "description": (
            "Returns discount effectiveness data: for each discount code, shows usage count, "
            "average activation value with and without the discount, and uplift percentage. "
            "Also returns overall: % of activations that used a discount, average discount depth. "
            "Use for questions about discount ROI, which discount works best, "
            "or whether discounts are profitable."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_meal_type_performance",
        "description": (
            "Returns meal type adoption: for each meal type (classic, veggie, protein, "
            "low_cal, quick, family), shows how many activations included at least one meal "
            "of that type and the percentage of total activations. "
            "Use for questions about popular meal types, meal type mix, "
            "or product preference at activation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "plan_filter": {
                    "type": "string",
                    "description": "Filter to activations with this plan name. Omit for all.",
                    "enum": ["classic", "veggie", "family", "protein",
                             "low_calorie", "quick_easy"],
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_activation_trend",
        "description": (
            "Returns activation volume and revenue over time, grouped by week or month. "
            "Each period shows: activation count, average activation value, total revenue. "
            "Use for questions about growth trends, seasonality, revenue over time, "
            "or week-over-week / month-over-month changes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "granularity": {
                    "type": "string",
                    "description": "Time grouping: 'week' or 'month'.",
                    "enum": ["week", "month"],
                    "default": "week",
                },
            },
            "required": [],
        },
    },
]


# ---------------------------------------------------------------------------
# Insights Agent tools
# ---------------------------------------------------------------------------

INSIGHTS_TOOLS: list[dict] = [
    {
        "name": "validate_metric",
        "description": (
            "Checks whether a given metric value is within the healthy benchmark range "
            "and returns a structured interpretation: status (healthy/warning/critical), "
            "benchmark_range (string), and interpretation (string explaining what the value means). "
            "ALWAYS call this before making any qualitative claim about a metric being 'good' or 'bad'. "
            "Never invent benchmark ranges — only use what this tool returns."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "metric_name": {
                    "type": "string",
                    "description": (
                        "The name of the metric to validate. Must be one of: "
                        "overall_cvr, landing_menu_ctr, menu_plan_ctr, plan_delivery_ctr, "
                        "delivery_account_ctr, account_payment_ctr, payment_confirmation_ctr, "
                        "mobile_cvr_vs_desktop, first_order_pct, avg_discount_depth, "
                        "classic_plan_pct, veggie_plan_pct."
                    ),
                    "enum": [
                        "overall_cvr",
                        "landing_menu_ctr",
                        "menu_plan_ctr",
                        "plan_delivery_ctr",
                        "delivery_account_ctr",
                        "account_payment_ctr",
                        "payment_confirmation_ctr",
                        "mobile_cvr_vs_desktop",
                        "first_order_pct",
                        "avg_discount_depth",
                        "classic_plan_pct",
                        "veggie_plan_pct",
                    ],
                },
                "value": {
                    "type": "number",
                    "description": "The actual metric value (e.g. 3.2 for 3.2%).",
                },
            },
            "required": ["metric_name", "value"],
        },
    },
]
