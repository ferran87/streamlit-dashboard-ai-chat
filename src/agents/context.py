"""
src/agents/context.py
---------------------
Builds the shared system-prompt context block injected into every agent API call.

The context block contains:
  - Live KPI snapshot (computed from DataFrames)
  - Funnel step CTRs (last 30 days)
  - Top activation plans
  - Discount usage summary
  - Anti-hallucination instruction

The Insights Agent receives this PLUS hardcoded benchmark ranges.
"""

from __future__ import annotations

from datetime import datetime, date, timedelta
import pandas as pd

# ---------------------------------------------------------------------------
# Hardcoded benchmarks (cannot be manipulated via data)
# ---------------------------------------------------------------------------
BENCHMARKS: dict[str, dict] = {
    "overall_cvr": {
        "healthy_min": 2.0, "healthy_max": 5.0,
        "poor_max": 1.5, "excellent_min": 6.0,
        "description": "Session → activation conversion rate (%)",
    },
    "landing_menu_ctr": {
        "healthy_min": 60.0, "healthy_max": 70.0,
        "poor_max": 50.0, "excellent_min": 75.0,
        "description": "Landing page → menu browse CTR (%)",
    },
    "menu_plan_ctr": {
        "healthy_min": 40.0, "healthy_max": 55.0,
        "poor_max": 30.0, "excellent_min": 60.0,
        "description": "Menu browse → plan selection CTR (%)",
    },
    "plan_delivery_ctr": {
        "healthy_min": 65.0, "healthy_max": 80.0,
        "poor_max": 55.0, "excellent_min": 85.0,
        "description": "Plan selection → delivery settings CTR (%)",
    },
    "delivery_account_ctr": {
        "healthy_min": 75.0, "healthy_max": 90.0,
        "poor_max": 65.0, "excellent_min": 92.0,
        "description": "Delivery settings → account creation CTR (%)",
    },
    "account_payment_ctr": {
        "healthy_min": 70.0, "healthy_max": 85.0,
        "poor_max": 60.0, "excellent_min": 88.0,
        "description": "Account creation → payment CTR (%)",
    },
    "payment_confirmation_ctr": {
        "healthy_min": 78.0, "healthy_max": 90.0,
        "poor_max": 70.0, "excellent_min": 92.0,
        "description": "Payment → confirmation CTR (%)",
    },
    "mobile_cvr_vs_desktop": {
        "healthy_min": -40.0, "healthy_max": -20.0,
        "poor_max": -50.0, "excellent_min": -10.0,
        "description": "Mobile CVR relative to desktop CVR (% difference — negative is expected)",
    },
    "first_order_pct": {
        "healthy_min": 65.0, "healthy_max": 75.0,
        "poor_max": 55.0, "excellent_min": 80.0,
        "description": "First orders as % of total activations",
    },
    "avg_discount_depth": {
        "healthy_min": 25.0, "healthy_max": 40.0,
        "poor_max": 50.0, "excellent_min": 20.0,
        "description": "Average discount as % of basket value",
    },
    "classic_plan_pct": {
        "healthy_min": 40.0, "healthy_max": 55.0,
        "poor_max": 30.0, "excellent_min": 60.0,
        "description": "Classic plan as % of activations",
    },
    "veggie_plan_pct": {
        "healthy_min": 15.0, "healthy_max": 25.0,
        "poor_max": 10.0, "excellent_min": 30.0,
        "description": "Veggie plan as % of activations",
    },
}


def validate_metric(metric_name: str, value: float) -> dict:
    """
    Used by the Insights Agent's validate_metric tool.
    Returns status, benchmark_range, and interpretation.
    """
    if metric_name not in BENCHMARKS:
        return {
            "status": "unknown",
            "benchmark_range": "No benchmark available",
            "interpretation": f"No benchmark defined for '{metric_name}'.",
        }

    b = BENCHMARKS[metric_name]
    healthy_min = b["healthy_min"]
    healthy_max = b["healthy_max"]

    if healthy_min <= value <= healthy_max:
        status = "healthy"
        interpretation = (
            f"{b['description']} is {value:.1f}%, within the healthy range "
            f"of {healthy_min}–{healthy_max}%."
        )
    elif value < healthy_min:
        status = "warning" if value > b.get("poor_max", healthy_min * 0.7) else "critical"
        interpretation = (
            f"{b['description']} is {value:.1f}%, below the healthy floor of {healthy_min}%. "
            f"This warrants investigation."
        )
    else:
        status = "excellent"
        interpretation = (
            f"{b['description']} is {value:.1f}%, above the healthy ceiling of {healthy_max}%. "
            f"This is excellent performance."
        )

    return {
        "status": status,
        "benchmark_range": f"{healthy_min}–{healthy_max}% (healthy)",
        "interpretation": interpretation,
    }


# ---------------------------------------------------------------------------
# Context block builder — with module-level cache
# ---------------------------------------------------------------------------

# Module-level cache: avoids recomputing expensive DataFrame aggregations on
# every API call. Invalidates automatically when dataset contents change.
_CONTEXT_CACHE: dict = {}


def _dataset_fingerprint(datasets: dict[str, pd.DataFrame]) -> tuple:
    """
    Fast fingerprint of the datasets dict.
    Uses (name, shape, first_cell, last_cell) per frame — cheap to compute,
    sufficient to detect data changes between Streamlit cache reloads.
    """
    parts = []
    for name in sorted(datasets.keys()):
        df = datasets[name]
        first = df.iat[0, 0] if len(df) > 0 and len(df.columns) > 0 else None
        last  = df.iat[-1, -1] if len(df) > 0 and len(df.columns) > 0 else None
        parts.append((name, df.shape, str(first), str(last)))
    return tuple(parts)


def build_context_block(datasets: dict[str, pd.DataFrame]) -> str:
    """
    Computes live KPIs from the DataFrames and returns a formatted string
    to be used as the 'system' prompt in every agent API call.

    Results are cached per dataset version (keyed on shape + boundary values)
    so the expensive aggregations only run once per loaded dataset.

    Gracefully falls back to placeholder values if metrics haven't been
    implemented yet (so the agent architecture works even before src/metrics.py
    is fully implemented).
    """
    fp = _dataset_fingerprint(datasets)
    if fp in _CONTEXT_CACHE:
        return _CONTEXT_CACHE[fp]
    result = _build_context_block_impl(datasets)
    _CONTEXT_CACHE[fp] = result
    return result


def _build_context_block_impl(datasets: dict[str, pd.DataFrame]) -> str:
    """Internal implementation — called only on cache miss."""
    df_sessions    = datasets.get("sessions", pd.DataFrame())
    df_activations = datasets.get("activations", pd.DataFrame())
    df_funnel      = datasets.get("funnel_steps", pd.DataFrame())

    # --- Compute live stats (with safe fallbacks) ---
    try:
        total_sessions    = len(df_sessions)
        total_activations = len(df_activations)
        overall_cvr       = (total_activations / total_sessions * 100) if total_sessions else 0.0

        date_min = str(df_sessions["session_date"].min()) if "session_date" in df_sessions.columns else "N/A"
        date_max = str(df_sessions["session_date"].max()) if "session_date" in df_sessions.columns else "N/A"

        avg_value     = df_activations["activation_value"].mean() if "activation_value" in df_activations.columns else 0.0
        total_revenue = df_activations["activation_value"].sum()  if "activation_value" in df_activations.columns else 0.0

        # Top channel by CVR
        if "channel" in df_sessions.columns and "activated" in df_sessions.columns:
            ch = (
                df_sessions.groupby("channel")
                .agg(sessions=("session_id", "count"), activations=("activated", "sum"))
                .assign(cvr=lambda x: x["activations"] / x["sessions"] * 100)
                .sort_values("cvr", ascending=False)
            )
            top_channel     = ch.index[0] if len(ch) else "N/A"
            top_channel_cvr = ch["cvr"].iloc[0] if len(ch) else 0.0
        else:
            top_channel, top_channel_cvr = "N/A", 0.0

        # Funnel step CTRs (last 30 days)
        funnel_lines = _compute_funnel_summary(df_funnel, df_sessions)

        # Plan breakdown
        plan_lines = _compute_plan_summary(df_activations)

        # Discount summary
        pct_discount = (
            df_activations["has_discount"].mean() * 100
            if "has_discount" in df_activations.columns else 0.0
        )
        avg_disc_pct = (
            df_activations.loc[df_activations["has_discount"] == True, "discount_pct"].mean()
            if "has_discount" in df_activations.columns and "discount_pct" in df_activations.columns
            else 0.0
        )

    except Exception:
        # If data model isn't generated yet, use safe defaults
        total_sessions = total_activations = 0
        overall_cvr = avg_value = total_revenue = top_channel_cvr = avg_disc_pct = pct_discount = 0.0
        date_min = date_max = "N/A"
        top_channel = "N/A"
        funnel_lines = "  (data not available)"
        plan_lines   = "  (data not available)"

    context = f"""=== HELLOFRESH FUNNEL ANALYTICS — LIVE DATA CONTEXT ===
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
Data window: {date_min} → {date_max}

--- TOP-LINE KPIs ---
Total Sessions:       {total_sessions:,}
Total Activations:    {total_activations:,}
Overall CVR:          {overall_cvr:.2f}%
Avg Activation Value: ${avg_value:.2f}
Total Revenue:        ${total_revenue:,.0f}
Top Channel:          {top_channel} ({top_channel_cvr:.1f}% CVR)

--- FUNNEL STEP CTRs (last 30 days) ---
{funnel_lines}

--- TOP ACTIVATION PLANS ---
{plan_lines}

--- DISCOUNT USAGE ---
{pct_discount:.0f}% of activations used a discount
Avg discount depth:   {avg_disc_pct:.0f}%

=== ANTI-HALLUCINATION RULES ===
1. NEVER invent or estimate any metric value.
2. If a number is not in this context block, call the appropriate tool to retrieve it.
3. Always cite the exact figure (from context or tool result) when making any quantitative claim.
4. If a tool returns no data for a given filter, say so explicitly — do NOT substitute a guess.
"""
    return context


def build_insights_context_block(datasets: dict[str, pd.DataFrame]) -> str:
    """
    Extended context for the Insights Agent: base context + benchmark reference table.
    """
    base = build_context_block(datasets)

    benchmark_table = "\n--- BENCHMARK REFERENCE ---\n"
    for name, b in BENCHMARKS.items():
        benchmark_table += (
            f"  {name}: healthy {b['healthy_min']}–{b['healthy_max']}% "
            f"| poor <{b.get('poor_max', '?')}% "
            f"| excellent >{b.get('excellent_min', '?')}%\n"
        )
    benchmark_table += (
        "\nIMPORTANT: Only interpret numbers that were provided to you by the Analytics Agent "
        "or that appear in the context above. Never invent data. "
        "Call validate_metric() before making any qualitative claim about performance.\n"
    )

    return base + benchmark_table


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_funnel_summary(df_funnel: pd.DataFrame, df_sessions: pd.DataFrame) -> str:
    """Compute step-by-step CTRs for the last 30 days."""
    try:
        if df_funnel.empty or "step_name" not in df_funnel.columns:
            return "  (funnel data not available)"

        # Filter last 30 days using session_date from df_sessions
        cutoff = date.today() - timedelta(days=30)
        if "session_date" in df_sessions.columns:
            recent_ids = df_sessions.loc[
                pd.to_datetime(df_sessions["session_date"]).dt.date >= cutoff,
                "session_id"
            ]
            df_recent = df_funnel[df_funnel["session_id"].isin(recent_ids)]
        else:
            df_recent = df_funnel

        step_counts = (
            df_recent.groupby("step_name")["session_id"]
            .nunique()
            .reindex([
                "landing", "menu_browse", "plan_selection",
                "delivery_settings", "account_creation", "payment", "confirmation"
            ])
            .fillna(0)
        )

        step_pairs = [
            ("landing",           "menu_browse",        "landing → menu browse"),
            ("menu_browse",       "plan_selection",     "menu browse → plan selection"),
            ("plan_selection",    "delivery_settings",  "plan selection → delivery"),
            ("delivery_settings", "account_creation",   "delivery → account creation"),
            ("account_creation",  "payment",            "account creation → payment"),
            ("payment",           "confirmation",       "payment → confirmation"),
        ]

        lines = []
        for from_step, to_step, label in step_pairs:
            from_n = step_counts.get(from_step, 0)
            to_n   = step_counts.get(to_step, 0)
            ctr    = (to_n / from_n * 100) if from_n else 0.0
            lines.append(f"  {label}: {ctr:.1f}%")

        return "\n".join(lines)
    except Exception:
        return "  (could not compute funnel CTRs)"


def _compute_plan_summary(df_activations: pd.DataFrame) -> str:
    """Compute plan breakdown for context block."""
    try:
        if df_activations.empty or "plan_name" not in df_activations.columns:
            return "  (activation data not available)"

        plan_grp = (
            df_activations.groupby("plan_name")
            .agg(
                count=("activation_id", "count"),
                avg_value=("activation_value", "mean"),
            )
            .sort_values("count", ascending=False)
            .head(4)
        )

        lines = []
        total = plan_grp["count"].sum()
        for plan, row in plan_grp.iterrows():
            pct = row["count"] / total * 100 if total else 0
            lines.append(
                f"  {plan}: {int(row['count'])} activations "
                f"({pct:.0f}%) | avg ${row['avg_value']:.2f}"
            )
        return "\n".join(lines)
    except Exception:
        return "  (could not compute plan summary)"
