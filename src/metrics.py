"""Pure metric functions — accepts DataFrames, returns DataFrames or scalars."""

from __future__ import annotations

import pandas as pd
from typing import Optional


# ---------------------------------------------------------------------------
# Funnel Metrics
# ---------------------------------------------------------------------------

_STEP_ORDER = [
    "landing", "menu_browse", "plan_selection",
    "delivery_settings", "account_creation", "payment", "confirmation",
]


def _step_session_counts(df_funnel: pd.DataFrame) -> pd.Series:
    """Unique sessions per funnel step, ordered by _STEP_ORDER."""
    return (
        df_funnel.groupby("step_name")["session_id"]
        .nunique()
        .reindex(_STEP_ORDER)
        .fillna(0)
        .astype(int)
    )


def get_funnel_ctr(
    df_funnel: pd.DataFrame,
    channel: Optional[str] = None,
    device: Optional[str] = None,
    date_range: Optional[tuple] = None,
    df_sessions: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Returns CTR per funnel step, optionally filtered by channel/device/date.
    Columns: step, step_order, sessions_reached, ctr_to_next, exit_rate
    """
    df = df_funnel.copy()

    if df_sessions is not None and (channel or device or date_range):
        filt = df_sessions.copy()
        if channel:
            filt = filt[filt["channel"] == channel]
        if device:
            filt = filt[filt["device"] == device]
        if date_range and len(date_range) == 2:
            filt = filt[
                (pd.to_datetime(filt["session_date"]) >= pd.to_datetime(date_range[0]))
                & (pd.to_datetime(filt["session_date"]) <= pd.to_datetime(date_range[1]))
            ]
        df = df[df["session_id"].isin(filt["session_id"])]

    step_counts = _step_session_counts(df)

    rows = []
    for i, step in enumerate(_STEP_ORDER):
        reached = int(step_counts.get(step, 0))
        if i < len(_STEP_ORDER) - 1:
            next_reached = int(step_counts.get(_STEP_ORDER[i + 1], 0))
            ctr = (next_reached / reached * 100) if reached > 0 else 0.0
        else:
            ctr = None
        exit_rate = (1 - ctr / 100) if ctr is not None else 0.0
        rows.append({
            "step": step,
            "step_order": i + 1,
            "sessions_reached": reached,
            "ctr_to_next": ctr,
            "exit_rate": round(exit_rate * 100, 2) if ctr is not None else 0.0,
        })

    return pd.DataFrame(rows)


def get_overall_conversion_rate(
    df_sessions: pd.DataFrame,
    channel: Optional[str] = None,
    device: Optional[str] = None,
) -> float:
    """Overall CVR = activated sessions / total sessions * 100."""
    df = df_sessions.copy()
    if channel:
        df = df[df["channel"] == channel]
    if device:
        df = df[df["device"] == device]
    if len(df) == 0:
        return 0.0
    return float(df["activated"].mean() * 100)


def get_conversion_by_channel(
    df_sessions: pd.DataFrame,
    df_activations: pd.DataFrame,
) -> pd.DataFrame:
    """Returns [channel, sessions, activations, cvr] sorted by cvr desc."""
    sess = df_sessions.groupby("channel")["session_id"].nunique().reset_index(name="sessions")
    acts = df_activations.groupby(
        df_activations["session_id"].map(
            df_sessions.set_index("session_id")["channel"]
        )
    )["activation_id"].nunique().reset_index(name="activations")
    acts.columns = ["channel", "activations"]

    merged = sess.merge(acts, on="channel", how="left").fillna({"activations": 0})
    merged["activations"] = merged["activations"].astype(int)
    merged["cvr"] = (merged["activations"] / merged["sessions"] * 100).round(2)
    return merged.sort_values("cvr", ascending=False).reset_index(drop=True)


def get_conversion_by_device(
    df_sessions: pd.DataFrame,
    df_activations: pd.DataFrame,
) -> pd.DataFrame:
    """Returns [device, sessions, activations, cvr] sorted by cvr desc."""
    sess = df_sessions.groupby("device")["session_id"].nunique().reset_index(name="sessions")

    session_device_map = df_sessions.set_index("session_id")["device"]
    act_devices = df_activations["session_id"].map(session_device_map)
    acts = act_devices.value_counts().reset_index()
    acts.columns = ["device", "activations"]

    merged = sess.merge(acts, on="device", how="left").fillna({"activations": 0})
    merged["activations"] = merged["activations"].astype(int)
    merged["cvr"] = (merged["activations"] / merged["sessions"] * 100).round(2)
    return merged.sort_values("cvr", ascending=False).reset_index(drop=True)


def get_funnel_drop_off(df_funnel: pd.DataFrame) -> pd.DataFrame:
    """Returns [step, step_order, dropped_sessions, drop_pct] per step."""
    step_counts = _step_session_counts(df_funnel)

    rows = []
    for i, step in enumerate(_STEP_ORDER):
        reached = int(step_counts.get(step, 0))
        if i < len(_STEP_ORDER) - 1:
            next_reached = int(step_counts.get(_STEP_ORDER[i + 1], 0))
            dropped = reached - next_reached
        else:
            dropped = 0
        drop_pct = (dropped / reached * 100) if reached > 0 else 0.0
        rows.append({
            "step": step,
            "step_order": i + 1,
            "dropped_sessions": dropped,
            "drop_pct": round(drop_pct, 2),
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Activation Metrics
# ---------------------------------------------------------------------------

def get_activation_value_by_plan(df_activations: pd.DataFrame) -> pd.DataFrame:
    """Returns [plan_name, count, avg_value, total_value] sorted by total_value desc."""
    grouped = (
        df_activations.groupby("plan_name")
        .agg(
            count=("activation_id", "count"),
            avg_value=("activation_value", "mean"),
            total_value=("activation_value", "sum"),
        )
        .reset_index()
    )
    grouped["avg_value"] = grouped["avg_value"].round(2)
    grouped["total_value"] = grouped["total_value"].round(2)
    return grouped.sort_values("total_value", ascending=False).reset_index(drop=True)


def get_activation_value_by_type(df_activations: pd.DataFrame) -> pd.DataFrame:
    """Returns [activation_type, count, avg_value, discount_rate] sorted by count desc."""
    grouped = (
        df_activations.groupby("activation_type")
        .agg(
            count=("activation_id", "count"),
            avg_value=("activation_value", "mean"),
            discount_rate=("has_discount", "mean"),
        )
        .reset_index()
    )
    grouped["avg_value"] = grouped["avg_value"].round(2)
    grouped["discount_rate"] = (grouped["discount_rate"] * 100).round(2)
    return grouped.sort_values("count", ascending=False).reset_index(drop=True)


def get_discount_effectiveness(
    df_activations: pd.DataFrame,
    df_discounts: pd.DataFrame,
) -> pd.DataFrame:
    """
    Per discount code: used_count, avg_value_with, avg_value_without, uplift_pct.
    Sorted by used_count desc.
    """
    avg_no_discount = df_activations.loc[
        ~df_activations["has_discount"], "activation_value"
    ].mean()
    if pd.isna(avg_no_discount):
        avg_no_discount = 0.0

    disc_acts = df_activations[df_activations["has_discount"]].copy()

    if disc_acts.empty:
        result = df_discounts[["discount_code", "discount_type"]].copy()
        result["used_count"] = 0
        result["avg_value_with"] = 0.0
        result["avg_value_without"] = avg_no_discount
        result["uplift_pct"] = 0.0
        return result

    by_code = (
        disc_acts.groupby("discount_code")
        .agg(
            used_count=("activation_id", "count"),
            avg_value_with=("activation_value", "mean"),
        )
        .reset_index()
    )

    result = df_discounts[["discount_code", "discount_type"]].merge(
        by_code, on="discount_code", how="left"
    )
    result["used_count"] = result["used_count"].fillna(0).astype(int)
    result["avg_value_with"] = result["avg_value_with"].fillna(0.0).round(2)
    result["avg_value_without"] = round(avg_no_discount, 2)
    result["uplift_pct"] = (
        ((result["avg_value_with"] - avg_no_discount) / avg_no_discount * 100)
        if avg_no_discount > 0 else 0.0
    )
    result["uplift_pct"] = result["uplift_pct"].round(2)
    return result.sort_values("used_count", ascending=False).reset_index(drop=True)


def get_meal_type_adoption(
    df_meals: pd.DataFrame,
    df_activations: pd.DataFrame,
) -> pd.DataFrame:
    """
    Per meal type: activation_count (unique activations that included it),
    pct_of_activations. Sorted by activation_count desc.
    """
    total_activations = df_activations["activation_id"].nunique()
    by_type = (
        df_meals.groupby("meal_type")["activation_id"]
        .nunique()
        .reset_index(name="activation_count")
    )
    by_type["pct_of_activations"] = (
        (by_type["activation_count"] / total_activations * 100).round(2)
    )
    return by_type.sort_values("activation_count", ascending=False).reset_index(drop=True)


def get_activation_trend(
    df_activations: pd.DataFrame,
    granularity: str = "week",
) -> pd.DataFrame:
    """
    Groups activations by week or month.
    Returns [period, activations, avg_value, total_revenue].
    """
    df = df_activations.copy()
    df["activation_date"] = pd.to_datetime(df["activation_date"])

    if granularity == "month":
        df["period"] = df["activation_date"].dt.to_period("M").astype(str)
    else:
        df["period"] = df["activation_date"].dt.to_period("W").dt.start_time.dt.strftime("%Y-%m-%d")

    grouped = (
        df.groupby("period")
        .agg(
            activations=("activation_id", "count"),
            avg_value=("activation_value", "mean"),
            total_revenue=("activation_value", "sum"),
        )
        .reset_index()
        .sort_values("period")
        .reset_index(drop=True)
    )
    grouped["avg_value"] = grouped["avg_value"].round(2)
    grouped["total_revenue"] = grouped["total_revenue"].round(2)
    return grouped


# ---------------------------------------------------------------------------
# Session Metrics
# ---------------------------------------------------------------------------

def get_session_volume_trend(df_sessions: pd.DataFrame) -> pd.DataFrame:
    """Weekly sessions, activated sessions, and CVR."""
    df = df_sessions.copy()
    df["session_date"] = pd.to_datetime(df["session_date"])
    df["week"] = df["session_date"].dt.to_period("W").dt.start_time.dt.strftime("%Y-%m-%d")

    grouped = (
        df.groupby("week")
        .agg(
            sessions=("session_id", "count"),
            activated_sessions=("activated", "sum"),
        )
        .reset_index()
        .sort_values("week")
        .reset_index(drop=True)
    )
    grouped["activated_sessions"] = grouped["activated_sessions"].astype(int)
    grouped["cvr"] = (grouped["activated_sessions"] / grouped["sessions"] * 100).round(2)
    return grouped


def get_cvr_trend_by_device(
    df_sessions: pd.DataFrame,
    granularity: str = "week",
) -> pd.DataFrame:
    """CVR over time broken down by device. Returns [period, device, sessions, activations, cvr]."""
    df = df_sessions.copy()
    df["session_date"] = pd.to_datetime(df["session_date"])

    if granularity == "month":
        df["period"] = df["session_date"].dt.to_period("M").astype(str)
    else:
        df["period"] = df["session_date"].dt.to_period("W").dt.start_time.dt.strftime("%Y-%m-%d")

    grouped = (
        df.groupby(["period", "device"])
        .agg(sessions=("session_id", "count"), activations=("activated", "sum"))
        .reset_index()
        .sort_values(["period", "device"])
        .reset_index(drop=True)
    )
    grouped["activations"] = grouped["activations"].astype(int)
    grouped["cvr"] = (grouped["activations"] / grouped["sessions"] * 100).round(2)
    return grouped


def get_kpi_summary(
    df_sessions: pd.DataFrame,
    df_funnel: pd.DataFrame,
    df_activations: pd.DataFrame,
    df_meals: pd.DataFrame,
    df_discounts: pd.DataFrame,
) -> dict:
    """All top-level KPIs as a flat dict."""
    total_sessions = len(df_sessions)
    total_activations = len(df_activations)
    overall_cvr = round(total_activations / total_sessions * 100, 2) if total_sessions else 0.0
    avg_activation_value = round(df_activations["activation_value"].mean(), 2) if total_activations else 0.0
    total_revenue = round(df_activations["activation_value"].sum(), 2) if total_activations else 0.0

    # Top channel by CVR
    ch = (
        df_sessions.groupby("channel")
        .agg(sessions=("session_id", "count"), activations=("activated", "sum"))
        .assign(cvr=lambda x: x["activations"] / x["sessions"] * 100)
        .sort_values("cvr", ascending=False)
    )
    top_channel = ch.index[0] if len(ch) else "N/A"
    top_channel_cvr = round(ch["cvr"].iloc[0], 2) if len(ch) else 0.0

    # Best/worst funnel step CTR
    funnel_df = get_funnel_ctr(df_funnel)
    funnel_with_ctr = funnel_df[funnel_df["ctr_to_next"].notna()].copy()
    if not funnel_with_ctr.empty:
        worst_row = funnel_with_ctr.loc[funnel_with_ctr["ctr_to_next"].idxmin()]
        best_row = funnel_with_ctr.loc[funnel_with_ctr["ctr_to_next"].idxmax()]
        worst_funnel_step = worst_row["step"]
        worst_funnel_ctr = round(worst_row["ctr_to_next"], 2)
        best_funnel_step = best_row["step"]
        best_funnel_ctr = round(best_row["ctr_to_next"], 2)
    else:
        worst_funnel_step = best_funnel_step = "N/A"
        worst_funnel_ctr = best_funnel_ctr = 0.0

    # Discount stats
    pct_with_discount = round(df_activations["has_discount"].mean() * 100, 2) if total_activations else 0.0
    disc_subset = df_activations.loc[df_activations["has_discount"], "discount_pct"]
    avg_discount_pct = round(disc_subset.mean(), 2) if len(disc_subset) else 0.0

    # Date range
    date_min = str(pd.to_datetime(df_sessions["session_date"]).min().date())
    date_max = str(pd.to_datetime(df_sessions["session_date"]).max().date())

    return {
        "total_sessions": total_sessions,
        "total_activations": total_activations,
        "overall_cvr": overall_cvr,
        "avg_activation_value": avg_activation_value,
        "total_revenue": total_revenue,
        "top_channel": top_channel,
        "top_channel_cvr": top_channel_cvr,
        "worst_funnel_step": worst_funnel_step,
        "worst_funnel_ctr": worst_funnel_ctr,
        "best_funnel_step": best_funnel_step,
        "best_funnel_ctr": best_funnel_ctr,
        "pct_with_discount": pct_with_discount,
        "avg_discount_pct": avg_discount_pct,
        "date_min": date_min,
        "date_max": date_max,
    }
