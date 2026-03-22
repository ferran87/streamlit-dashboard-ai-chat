"""
data/generate.py
----------------
Deterministic HelloFresh mock data generator.
Run standalone:  python -m data.generate
                 python -m data.generate --force   (re-generate even if files exist)

Produces 5 parquet files in data/raw/:
  sessions.parquet        ~50 000 rows
  funnel_steps.parquet    ~150 000 rows
  activations.parquet     ~1 500 rows
  meal_selections.parquet ~5 000 rows
  discounts.parquet       ~15 rows (catalogue)

All randomness uses seed=42 for reproducibility.
"""

import argparse
import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

# ---------------------------------------------------------------------------
# Seeds & paths
# ---------------------------------------------------------------------------
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

OUTPUT_DIR = Path(__file__).parent / "raw"

# ---------------------------------------------------------------------------
# Constants (match docs/PLAN.md schema)
# ---------------------------------------------------------------------------
CHANNELS = ["organic_search", "paid_search", "paid_social", "email", "referral", "direct"]
CHANNEL_WEIGHTS = [0.30, 0.25, 0.20, 0.10, 0.08, 0.07]

DEVICES = ["mobile", "desktop", "tablet"]
DEVICE_WEIGHTS = [0.55, 0.35, 0.10]

COUNTRIES = ["DE", "US", "GB", "AU", "NL", "AT", "BE", "CH"]
COUNTRY_WEIGHTS = [0.30, 0.25, 0.15, 0.10, 0.07, 0.05, 0.05, 0.03]

UTM_SOURCES = ["google", "facebook", "instagram", "newsletter", "partner", None]
UTM_CAMPAIGNS = ["brand", "non_brand", "retargeting", "welcome_back", None]

LANDING_PAGES = ["homepage", "menu", "offer", "blog", "referral_landing"]
LANDING_WEIGHTS = [0.40, 0.25, 0.20, 0.10, 0.05]

FUNNEL_STEPS = [
    "landing",
    "menu_browse",
    "plan_selection",
    "delivery_settings",
    "account_creation",
    "payment",
    "confirmation",
]

# Baseline CTR from step N → step N+1 (index 0 = landing→menu_browse, etc.)
BASELINE_CTRS = [0.65, 0.45, 0.70, 0.80, 0.75, 0.82]

ACTIVATION_TYPES = ["first_order", "reactivation", "referral", "gift"]
ACTIVATION_TYPE_WEIGHTS = [0.70, 0.20, 0.08, 0.02]

PLAN_NAMES = ["classic", "veggie", "family", "protein", "low_calorie", "quick_easy"]
PLAN_WEIGHTS = [0.45, 0.20, 0.15, 0.10, 0.05, 0.05]

MEAL_TYPES = ["classic", "veggie", "protein", "low_cal", "quick", "family"]
CUISINES = ["italian", "asian", "mexican", "american", "mediterranean"]

DISCOUNT_CATALOGUE = [
    {"discount_code": "WELCOME50", "discount_type": "percentage", "discount_value": 50, "channel_target": "paid_search"},
    {"discount_code": "WELCOME40", "discount_type": "percentage", "discount_value": 40, "channel_target": "paid_social"},
    {"discount_code": "WELCOME30", "discount_type": "percentage", "discount_value": 30, "channel_target": "organic_search"},
    {"discount_code": "FREEBOX",   "discount_type": "free_box",    "discount_value": 0,  "channel_target": "referral"},
    {"discount_code": "20OFF",     "discount_type": "fixed_amount","discount_value": 20, "channel_target": "email"},
    {"discount_code": "15OFF",     "discount_type": "fixed_amount","discount_value": 15, "channel_target": "email"},
    {"discount_code": "REACTIVATE35", "discount_type": "percentage","discount_value": 35,"channel_target": "email"},
    {"discount_code": "REFER25",   "discount_type": "percentage",  "discount_value": 25, "channel_target": "referral"},
    {"discount_code": "VEGGIE20",  "discount_type": "percentage",  "discount_value": 20, "channel_target": "paid_social"},
    {"discount_code": "SUMMER10",  "discount_type": "percentage",  "discount_value": 10, "channel_target": "direct"},
]

MEAL_CATALOGUE = [
    # (meal_id, meal_name, meal_type, price_per_serving, cuisine)
    ("M001", "Honey Garlic Chicken",           "classic",  6.50, "asian"),
    ("M002", "Mushroom Risotto",                "veggie",   7.20, "italian"),
    ("M003", "Beef Tacos",                      "classic",  7.80, "mexican"),
    ("M004", "Salmon with Lemon Butter",        "protein",  9.00, "american"),
    ("M005", "Veggie Stir Fry",                 "veggie",   5.90, "asian"),
    ("M006", "Chicken Caesar Wrap",             "quick",    6.20, "american"),
    ("M007", "Lamb Kofta with Tzatziki",        "protein",  8.50, "mediterranean"),
    ("M008", "Pasta Primavera",                 "veggie",   6.00, "italian"),
    ("M009", "BBQ Pork Ribs",                   "family",   8.90, "american"),
    ("M010", "Thai Green Curry",                "classic",  7.10, "asian"),
    ("M011", "Zucchini Noodles with Pesto",     "low_cal",  5.50, "italian"),
    ("M012", "Chicken Shawarma Bowl",           "protein",  7.40, "mediterranean"),
    ("M013", "Mac and Cheese",                  "family",   5.80, "american"),
    ("M014", "Teriyaki Salmon Bowl",            "protein",  8.70, "asian"),
    ("M015", "Caprese Stuffed Chicken",         "classic",  7.60, "italian"),
    ("M016", "Black Bean Burrito",              "veggie",   5.70, "mexican"),
    ("M017", "Butter Chicken",                  "classic",  7.30, "asian"),
    ("M018", "Greek Salad with Halloumi",       "low_cal",  6.10, "mediterranean"),
    ("M019", "Beef Bolognese",                  "family",   7.00, "italian"),
    ("M020", "Shrimp Tacos",                    "quick",    7.90, "mexican"),
    ("M021", "Spinach Falafel Wrap",            "veggie",   5.60, "mediterranean"),
    ("M022", "Korean Bibimbap",                 "classic",  7.50, "asian"),
    ("M023", "Turkey Meatballs",                "protein",  7.20, "american"),
    ("M024", "Cauliflower Tikka Masala",        "veggie",   6.40, "asian"),
    ("M025", "Chicken Enchiladas",              "family",   6.90, "mexican"),
    ("M026", "Smoked Salmon Bagel",             "quick",    8.20, "american"),
    ("M027", "Eggplant Parmigiana",             "veggie",   6.30, "italian"),
    ("M028", "Steak with Chimichurri",          "protein",  9.50, "american"),
    ("M029", "Veggie Pad Thai",                 "low_cal",  5.80, "asian"),
    ("M030", "Fish and Chips",                  "family",   7.70, "american"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Weighted hours 7–22 (peaks at lunch 12–13 and dinner 17–18)
_HOUR_RANGE = list(range(7, 23))
_HOUR_WEIGHTS = np.array([1, 2, 3, 4, 5, 6, 6, 5, 4, 5, 6, 6, 5, 3, 2, 1], dtype=float)
_HOUR_WEIGHTS /= _HOUR_WEIGHTS.sum()

# Poisson lambdas for time_on_step_seconds per funnel step
_STEP_TIME_LAMBDAS = [30, 120, 90, 60, 45, 40, 15]

# Plan → preferred meal-type weights (for meal selection generation)
_PLAN_TYPE_WEIGHTS = {
    "classic":     {"classic": 0.40, "quick": 0.20, "veggie": 0.10, "protein": 0.10, "low_cal": 0.05, "family": 0.15},
    "veggie":      {"veggie": 0.50, "low_cal": 0.25, "classic": 0.10, "quick": 0.10, "protein": 0.03, "family": 0.02},
    "family":      {"family": 0.40, "classic": 0.25, "quick": 0.15, "veggie": 0.10, "protein": 0.05, "low_cal": 0.05},
    "protein":     {"protein": 0.50, "classic": 0.15, "low_cal": 0.15, "quick": 0.10, "veggie": 0.05, "family": 0.05},
    "low_calorie": {"low_cal": 0.40, "veggie": 0.30, "classic": 0.10, "quick": 0.10, "protein": 0.05, "family": 0.05},
    "quick_easy":  {"quick": 0.40, "classic": 0.25, "veggie": 0.10, "protein": 0.10, "low_cal": 0.10, "family": 0.05},
}

# Meals indexed by type for fast lookup
_MEALS_BY_TYPE: dict[str, list] = {}
for _m in MEAL_CATALOGUE:
    _MEALS_BY_TYPE.setdefault(_m[2], []).append(_m)
_ALL_MEAL_TYPES = sorted(_MEALS_BY_TYPE.keys())

# Average meal price per plan (used for activation value calculation)
_PLAN_PREFERRED_TYPES = {
    "classic": ["classic", "quick"],
    "veggie": ["veggie", "low_cal"],
    "family": ["family", "classic"],
    "protein": ["protein"],
    "low_calorie": ["low_cal", "veggie"],
    "quick_easy": ["quick", "classic"],
}
_PLAN_AVG_PRICE: dict[str, float] = {}
for _plan, _types in _PLAN_PREFERRED_TYPES.items():
    _prices = [m[3] for m in MEAL_CATALOGUE if m[2] in _types]
    _PLAN_AVG_PRICE[_plan] = sum(_prices) / len(_prices) if _prices else 7.0

# Channel → discount codes available
_CHANNEL_DISCOUNTS: dict[str, list[dict]] = {}
for _d in DISCOUNT_CATALOGUE:
    _CHANNEL_DISCOUNTS.setdefault(_d["channel_target"], []).append(_d)


def _assign_utm(channels: list[str]) -> tuple[list, list]:
    """Map channel array to aligned utm_source and utm_campaign arrays."""
    sources, campaigns = [], []
    for ch in channels:
        if ch == "organic_search":
            sources.append("google")
            campaigns.append(None)
        elif ch == "paid_search":
            sources.append("google")
            campaigns.append(random.choice(["brand", "non_brand"]))
        elif ch == "paid_social":
            sources.append(random.choice(["facebook", "instagram"]))
            campaigns.append(random.choice(["retargeting", "non_brand"]))
        elif ch == "email":
            sources.append("newsletter")
            campaigns.append(random.choice(["welcome_back", "retargeting"]))
        elif ch == "referral":
            sources.append("partner")
            campaigns.append(None)
        else:
            sources.append(None)
            campaigns.append(None)
    return sources, campaigns


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

def generate_sessions(n: int = 50_000) -> pd.DataFrame:
    """Generate prospect browsing sessions with funnel simulation."""

    # --- Session IDs ---
    session_ids = [fake.uuid4() for _ in range(n)]

    # --- Visitor IDs (~30 % reuse) ---
    n_unique = int(n * 0.70)
    unique_visitors = [fake.uuid4() for _ in range(n_unique)]
    reuse_visitors = [random.choice(unique_visitors) for _ in range(n - n_unique)]
    visitor_ids = unique_visitors + reuse_visitors
    random.shuffle(visitor_ids)

    # --- Dates (last 12 months) ---
    today = date.today()
    start = today - timedelta(days=365)
    random_days = np.random.randint(0, 366, size=n)
    session_dates = [start + timedelta(days=int(d)) for d in random_days]

    # --- Datetimes (weighted hours 7–22) ---
    hours = np.random.choice(_HOUR_RANGE, size=n, p=_HOUR_WEIGHTS)
    minutes = np.random.randint(0, 60, size=n)
    seconds = np.random.randint(0, 60, size=n)
    session_datetimes = [
        pd.Timestamp(d.year, d.month, d.day, int(h), int(mi), int(s))
        for d, h, mi, s in zip(session_dates, hours, minutes, seconds)
    ]

    # --- Categorical columns ---
    channels = list(np.random.choice(CHANNELS, size=n, p=CHANNEL_WEIGHTS))
    devices = list(np.random.choice(DEVICES, size=n, p=DEVICE_WEIGHTS))
    countries = list(np.random.choice(COUNTRIES, size=n, p=COUNTRY_WEIGHTS))
    landing_pages = list(np.random.choice(LANDING_PAGES, size=n, p=LANDING_WEIGHTS))
    utm_sources, utm_campaigns = _assign_utm(channels)

    # --- Funnel simulation (vectorised) ---
    # For each session and each of the 6 gates, apply CTR + Gaussian noise ±5pp
    gate_noise = np.random.normal(0, 0.05, size=(n, 6))
    gate_probs = np.clip(np.array(BASELINE_CTRS) + gate_noise, 0.01, 0.99)
    gate_draws = np.random.random(size=(n, 6))
    gate_passed = gate_draws < gate_probs
    # cumulative AND: True at position k iff all gates 0..k passed
    cumulative_passed = np.cumprod(gate_passed, axis=1)
    # last_step_order: 1 (landing only) to 7 (reached confirmation)
    last_step_orders = (1 + cumulative_passed.sum(axis=1)).astype(int)
    activated = last_step_orders == 7

    return pd.DataFrame({
        "session_id": session_ids,
        "visitor_id": visitor_ids,
        "session_date": session_dates,
        "session_datetime": session_datetimes,
        "channel": channels,
        "device": devices,
        "country": countries,
        "utm_source": utm_sources,
        "utm_campaign": utm_campaigns,
        "landing_page": landing_pages,
        "activated": activated,
        "_last_step_order": last_step_orders,
    })


def generate_funnel_steps(df_sessions: pd.DataFrame) -> pd.DataFrame:
    """
    For each session, generate one row per reached funnel step.
    Uses _last_step_order from df_sessions to know how far each session went.
    """
    frames = []

    for step_idx in range(7):
        step_order = step_idx + 1
        step_name = FUNNEL_STEPS[step_idx]

        mask = df_sessions["_last_step_order"] >= step_order
        subset = df_sessions.loc[mask]
        n_sub = len(subset)
        if n_sub == 0:
            continue

        is_last = subset["_last_step_order"].values == step_order
        exited = is_last & (step_order < 7)
        time_on_step = np.maximum(1, np.random.poisson(_STEP_TIME_LAMBDAS[step_idx], size=n_sub))

        frames.append(pd.DataFrame({
            "session_id": subset["session_id"].values,
            "step_name": step_name,
            "step_order": step_order,
            "reached": True,
            "exited": exited,
            "time_on_step_seconds": time_on_step,
        }))

    df = pd.concat(frames, ignore_index=True)

    # Compute aggregate CTR per step (sessions reaching next / sessions reaching this)
    step_counts = df.groupby("step_order")["session_id"].nunique().sort_index()
    ctr_map: dict[int, float | None] = {}
    for order in range(1, 7):
        curr = step_counts.get(order, 0)
        nxt = step_counts.get(order + 1, 0)
        ctr_map[order] = round(nxt / curr * 100, 2) if curr else 0.0
    ctr_map[7] = None

    df["ctr"] = df["step_order"].map(ctr_map)
    df = df.sort_values(["session_id", "step_order"]).reset_index(drop=True)
    return df


def generate_activations(df_sessions: pd.DataFrame) -> pd.DataFrame:
    """One row per session that reached confirmation (activated=True)."""
    activated = df_sessions[df_sessions["activated"]].copy()
    n = len(activated)

    activation_ids = [fake.uuid4() for _ in range(n)]
    activation_types = np.random.choice(ACTIVATION_TYPES, size=n, p=ACTIVATION_TYPE_WEIGHTS)
    plan_names = np.random.choice(PLAN_NAMES, size=n, p=PLAN_WEIGHTS)
    meals_pw = np.random.choice([2, 3, 4, 5], size=n, p=[0.15, 0.40, 0.30, 0.15])
    portions = np.random.choice([2, 4], size=n, p=[0.55, 0.45])

    avg_prices = np.array([_PLAN_AVG_PRICE.get(p, 7.0) for p in plan_names])

    # ~60 % of activations have a discount
    has_discount = np.random.random(n) < 0.60

    channels = activated["channel"].values
    discount_codes: list[str | None] = []
    discount_types: list[str | None] = []
    discount_amounts: list[float] = []
    discount_pcts: list[float] = []

    for i in range(n):
        if not has_discount[i]:
            discount_codes.append(None)
            discount_types.append(None)
            discount_amounts.append(0.0)
            discount_pcts.append(0.0)
            continue

        available = _CHANNEL_DISCOUNTS.get(channels[i], [])
        disc = random.choice(available) if available else random.choice(DISCOUNT_CATALOGUE)
        gross = float(meals_pw[i]) * float(portions[i]) * avg_prices[i]

        discount_codes.append(disc["discount_code"])
        discount_types.append(disc["discount_type"])

        if disc["discount_type"] == "percentage":
            pct = float(disc["discount_value"])
            amt = gross * pct / 100
        elif disc["discount_type"] == "fixed_amount":
            amt = min(float(disc["discount_value"]), gross * 0.80)
            pct = (amt / gross * 100) if gross > 0 else 0.0
        else:  # free_box — modelled as ~65 % discount on first box
            pct = 65.0
            amt = gross * 0.65

        discount_amounts.append(round(amt, 2))
        discount_pcts.append(round(pct, 2))

    discount_factor = 1 - np.array(discount_pcts) / 100
    activation_values = np.round(
        meals_pw.astype(float) * portions.astype(float) * avg_prices * discount_factor, 2
    )

    return pd.DataFrame({
        "activation_id": activation_ids,
        "session_id": activated["session_id"].values,
        "visitor_id": activated["visitor_id"].values,
        "activation_date": activated["session_date"].values,
        "activation_type": activation_types,
        "plan_name": plan_names,
        "meals_per_week": meals_pw,
        "portions": portions,
        "activation_value": activation_values,
        "has_discount": has_discount,
        "discount_code": discount_codes,
        "discount_type": discount_types,
        "discount_amount": np.array(discount_amounts),
        "discount_pct": np.array(discount_pcts),
    })


def generate_meal_selections(df_activations: pd.DataFrame) -> pd.DataFrame:
    """Pick meals_per_week meals per activation, influenced by plan type."""
    rows: list[dict] = []

    for _, act in df_activations.iterrows():
        plan = act["plan_name"]
        n_meals = int(act["meals_per_week"])
        weights_map = _PLAN_TYPE_WEIGHTS.get(
            plan, {t: 1.0 / len(_ALL_MEAL_TYPES) for t in _ALL_MEAL_TYPES}
        )
        w = np.array([weights_map.get(t, 0.01) for t in _ALL_MEAL_TYPES])
        w /= w.sum()

        chosen_types = np.random.choice(_ALL_MEAL_TYPES, size=n_meals, p=w)
        for ct in chosen_types:
            meal = random.choice(_MEALS_BY_TYPE[ct])
            rows.append({
                "activation_id": act["activation_id"],
                "meal_id": meal[0],
                "meal_name": meal[1],
                "meal_type": meal[2],
                "price_per_serving": meal[3],
                "cuisine": meal[4],
            })

    return pd.DataFrame(rows)


def generate_discounts(df_activations: pd.DataFrame) -> pd.DataFrame:
    """Discount catalogue enriched with usage stats from activations."""
    cat = pd.DataFrame(DISCOUNT_CATALOGUE)

    disc_used = df_activations[df_activations["has_discount"]].copy()
    if not disc_used.empty and "discount_code" in disc_used.columns:
        usage = (
            disc_used.groupby("discount_code")
            .agg(
                activations_used=("activation_id", "count"),
                avg_activation_value=("activation_value", "mean"),
            )
            .reset_index()
        )
        cat = cat.merge(usage, on="discount_code", how="left")
    else:
        cat["activations_used"] = 0
        cat["avg_activation_value"] = 0.0

    cat["activations_used"] = cat["activations_used"].fillna(0).astype(int)
    cat["avg_activation_value"] = cat["avg_activation_value"].fillna(0.0).round(2)
    return cat


def generate_all(force: bool = False) -> dict[str, pd.DataFrame]:
    """
    Generate all datasets and write to OUTPUT_DIR as parquet.
    Skips generation if files already exist (unless force=True).
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    files = {
        "sessions": OUTPUT_DIR / "sessions.parquet",
        "funnel_steps": OUTPUT_DIR / "funnel_steps.parquet",
        "activations": OUTPUT_DIR / "activations.parquet",
        "meal_selections": OUTPUT_DIR / "meal_selections.parquet",
        "discounts": OUTPUT_DIR / "discounts.parquet",
    }

    if not force and all(p.exists() for p in files.values()):
        print("Parquet files already exist. Use --force to regenerate.")
        return {k: pd.read_parquet(v) for k, v in files.items()}

    print("Generating sessions...")
    df_sessions = generate_sessions()

    print("Generating funnel steps...")
    df_funnel = generate_funnel_steps(df_sessions)

    # Drop internal column before persisting
    df_sessions = df_sessions.drop(columns=["_last_step_order"])
    df_sessions.to_parquet(files["sessions"], index=False)
    df_funnel.to_parquet(files["funnel_steps"], index=False)

    print("Generating activations...")
    df_activations = generate_activations(df_sessions)
    df_activations.to_parquet(files["activations"], index=False)

    print("Generating meal selections...")
    df_meals = generate_meal_selections(df_activations)
    df_meals.to_parquet(files["meal_selections"], index=False)

    print("Generating discounts catalogue...")
    df_discounts = generate_discounts(df_activations)
    df_discounts.to_parquet(files["discounts"], index=False)

    print(f"Done. Files written to {OUTPUT_DIR}")
    return {
        "sessions": df_sessions,
        "funnel_steps": df_funnel,
        "activations": df_activations,
        "meal_selections": df_meals,
        "discounts": df_discounts,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Regenerate even if files exist")
    args = parser.parse_args()
    generate_all(force=args.force)
