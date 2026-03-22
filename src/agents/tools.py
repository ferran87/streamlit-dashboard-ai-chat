"""Anthropic tool schemas for the unified agent. Each tool maps to src/metrics.py."""

from __future__ import annotations

# Shared date-range properties added to every analytics tool and the chart tool.
# The agent reads the data window from the LIVE CONTEXT block and computes ISO dates.
_DATE_PROPS: dict = {
    "date_range_start": {
        "type": "string",
        "description": (
            "ISO date string (YYYY-MM-DD). Filter data to sessions/activations on or "
            "after this date. Compute from the LIVE DATA CONTEXT 'Data window' line. "
            "Pass the same value to every tool call in this turn."
        ),
    },
    "date_range_end": {
        "type": "string",
        "description": (
            "ISO date string (YYYY-MM-DD). Filter data to sessions/activations on or "
            "before this date. Compute from the LIVE DATA CONTEXT 'Data window' line. "
            "Pass the same value to every tool call in this turn."
        ),
    },
}

# ---------------------------------------------------------------------------
# Data query tools (8)
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
            "properties": {**_DATE_PROPS},
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
                **_DATE_PROPS,
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
            "properties": {**_DATE_PROPS},
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
            "properties": {**_DATE_PROPS},
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
                **_DATE_PROPS,
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
            "properties": {**_DATE_PROPS},
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
                **_DATE_PROPS,
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
                **_DATE_PROPS,
            },
            "required": [],
        },
    },
    {
        "name": "get_session_volume_trend",
        "description": (
            "Returns weekly session volume with conversion data: total sessions, "
            "activated sessions, and CVR (%) per week. "
            "Use for questions about weekly conversion rate trends, session volume over time, "
            "week-over-week CVR changes, or any time-series question that needs a per-week "
            "session denominator."
        ),
        "input_schema": {
            "type": "object",
            "properties": {**_DATE_PROPS},
            "required": [],
        },
    },
    {
        "name": "get_cvr_trend_by_device",
        "description": (
            "Returns conversion rate (CVR %) trend broken down by device type "
            "(mobile, desktop, tablet) over time, grouped by week or month. "
            "Each row: period, device, sessions, activations, cvr. "
            "Use when the user asks for weekly/monthly CVR by device, device CVR trends, "
            "or how device-level conversion changes over time."
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
                **_DATE_PROPS,
            },
            "required": [],
        },
    },
]


# ---------------------------------------------------------------------------
# Validation tool
# ---------------------------------------------------------------------------

INSIGHTS_TOOLS: list[dict] = [
    {
        "name": "validate_metric",
        "description": (
            "Checks whether a metric value falls within its benchmark range and returns "
            "a structured assessment: status (healthy/warning/critical/excellent/no_benchmark), "
            "benchmark_range, interpretation, confidence (high/moderate/low/very_low), "
            "and optionally sample_caveat.\n\n"
            "ALWAYS call this before making any qualitative claim about a metric being "
            "'good', 'bad', 'healthy', 'concerning', or 'excellent'.\n\n"
            "Benchmarks exist for these 12 metrics (pass the exact name):\n"
            "  overall_cvr, landing_menu_ctr, menu_plan_ctr, plan_delivery_ctr,\n"
            "  delivery_account_ctr, account_payment_ctr, payment_confirmation_ctr,\n"
            "  mobile_cvr_vs_desktop, first_order_pct, avg_discount_depth,\n"
            "  classic_plan_pct, veggie_plan_pct.\n\n"
            "For any other metric (WoW growth, per-discount-code CVR, cross-segment rates, "
            "meal type adoption %, etc.), still call this tool with a descriptive name — "
            "it returns status='no_benchmark' with explicit guidance on how to report the "
            "value without qualitative labels. Never errors on unknown metric names."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "metric_name": {
                    "type": "string",
                    "description": (
                        "Metric identifier. The 12 names listed above return benchmark ranges. "
                        "For any other metric (e.g. 'wow_growth_rate', 'discount_SUMMER20_cvr', "
                        "'referral_mobile_cvr', 'meal_type_veggie_pct'), pass a descriptive name — "
                        "the tool returns status='no_benchmark' with explicit reporting guidance. "
                        "Accepts any string — never errors on unknown names."
                    ),
                    # No enum — accepts any string. The 12 known benchmark names are listed
                    # in the description above so the model knows which ones return health assessments.
                },
                "value": {
                    "type": "number",
                    "description": "The actual metric value (e.g. 3.2 for 3.2%).",
                },
                "n": {
                    "type": "integer",
                    "description": (
                        "Optional sample size driving this metric value. "
                        "Read from: sessions_reached (funnel tools), sessions or activations "
                        "(channel/device tools), used_count (discount tools), "
                        "activation_count (meal type tools). "
                        "When provided, returns a confidence tier (high/moderate/low/very_low) "
                        "and, for small samples, a sample_caveat string to include in your response."
                    ),
                },
            },
            "required": ["metric_name", "value"],
        },
    },
]


# ---------------------------------------------------------------------------
# generate_chart tool (used by the Unified Agent)
# ---------------------------------------------------------------------------

GENERATE_CHART_TOOL: dict = {
    "name": "generate_chart",
    "description": (
        "Generates a Plotly chart and displays it inline in the chat, above your text response. "
        "Call this when a visual would communicate comparisons, trends, or rankings more clearly "
        "than numbers in text. Call at most ONCE per turn. "
        "Available chart types:\n"
        "- funnel_steps_bar: sessions reached per funnel step (coloured by CTR health)\n"
        "- funnel_drop_off_waterfall: sessions lost at each step\n"
        "- activation_trend_line: activations count + avg value over time\n"
        "- activation_type_pie: split by first_order / reactivation / referral / gift\n"
        "- cvr_by_channel_bar: sessions, activations, and CVR% by acquisition channel\n"
        "- cvr_by_device_bar: CVR% by device (mobile / desktop / tablet)\n"
        "- activation_value_by_plan: total revenue and avg basket by plan\n"
        "- meal_type_adoption_bar: % of activations that included each meal type\n"
        "- discount_effectiveness: table of discount codes with uplift vs no-discount baseline\n"
        "- session_volume_trend: weekly activated vs non-activated session stacked area\n"
        "- cvr_trend_line: weekly conversion rate (%) as a line chart over time\n"
        "- cvr_trend_by_device_line: weekly CVR trend with one line per device (mobile/desktop/tablet)"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "chart_type": {
                "type": "string",
                "description": "The type of chart to generate.",
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
                    "cvr_trend_line",
                    "cvr_trend_by_device_line",
                ],
            },
            "channel": {
                "type": "string",
                "description": "Filter funnel_steps_bar by acquisition channel (optional).",
                "enum": [
                    "organic_search", "paid_search", "paid_social",
                    "email", "referral", "direct",
                ],
            },
            "device": {
                "type": "string",
                "description": "Filter funnel_steps_bar by device (optional).",
                "enum": ["mobile", "desktop", "tablet"],
            },
            "granularity": {
                "type": "string",
                "description": "Time grouping for activation_trend_line: 'week' or 'month'.",
                "enum": ["week", "month"],
            },
            **_DATE_PROPS,
        },
        "required": ["chart_type"],
    },
}


# ---------------------------------------------------------------------------
# Unified tools list — all tools available to the single Unified Agent
# ---------------------------------------------------------------------------

UNIFIED_TOOLS: list[dict] = ANALYTICS_TOOLS + INSIGHTS_TOOLS + [GENERATE_CHART_TOOL]
