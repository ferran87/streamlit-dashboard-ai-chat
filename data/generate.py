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
# Generators
# ---------------------------------------------------------------------------

def generate_sessions(n: int = 50_000) -> pd.DataFrame:
    """
    TODO (Cursor): Implement session generation.

    Each row = one prospect browsing session.
    - session_id: UUID4
    - visitor_id: UUID4 (visitors can have 1–3 sessions; reuse ~30% of visitor IDs)
    - session_date: random date in last 12 months (from today)
    - session_datetime: session_date + random hour weighted 7–22h
    - channel: weighted choice from CHANNELS / CHANNEL_WEIGHTS
    - device: weighted choice from DEVICES / DEVICE_WEIGHTS
    - country: weighted choice from COUNTRIES / COUNTRY_WEIGHTS
    - utm_source: aligned with channel (google for paid_search, etc.)
    - utm_campaign: random from UTM_CAMPAIGNS
    - landing_page: weighted choice from LANDING_PAGES / LANDING_WEIGHTS
    - activated: bool — determined by funnel simulation (see generate_funnel_steps)
    """
    raise NotImplementedError("TODO: implement generate_sessions()")


def generate_funnel_steps(df_sessions: pd.DataFrame) -> pd.DataFrame:
    """
    TODO (Cursor): Implement funnel step generation.

    For each session, simulate which funnel steps were reached using BASELINE_CTRS
    (add Gaussian noise ±5% per step). Only generate rows for reached steps.
    The last reached step has exited=True; all others have exited=False.
    Activated sessions must reach the 'confirmation' step.

    Columns: session_id, step_name, step_order, reached (always True),
             exited (bool), time_on_step_seconds (Poisson), ctr (float).

    NOTE: CTR on a row means CTR from THIS step to the NEXT step.
          The final step (confirmation) has ctr=None.
    """
    raise NotImplementedError("TODO: implement generate_funnel_steps()")


def generate_activations(df_sessions: pd.DataFrame) -> pd.DataFrame:
    """
    TODO (Cursor): Implement activation generation.

    One row per session where activated=True.
    - activation_id: UUID4
    - session_id, visitor_id: from df_sessions
    - activation_date: same as session_date
    - activation_type: weighted from ACTIVATION_TYPES / ACTIVATION_TYPE_WEIGHTS
    - plan_name: weighted from PLAN_NAMES / PLAN_WEIGHTS
    - meals_per_week: random choice [2, 3, 4, 5]
    - portions: random choice [2, 4]
    - has_discount: True for ~60% of activations
    - discount_code / discount_type: pick from DISCOUNT_CATALOGUE (align to channel)
    - discount_amount / discount_pct: computed from discount catalogue entry
    - activation_value: meals_per_week * portions * avg_meal_price * (1 - discount_pct/100)
      where avg_meal_price is drawn from meal catalogue for the plan
    """
    raise NotImplementedError("TODO: implement generate_activations()")


def generate_meal_selections(df_activations: pd.DataFrame) -> pd.DataFrame:
    """
    TODO (Cursor): Implement meal selection generation.

    For each activation, pick meals_per_week meals from MEAL_CATALOGUE.
    Meal type distribution should be influenced by plan_name
    (veggie plan → more veggie meals, protein plan → more protein meals).

    Columns: activation_id, meal_id, meal_name, meal_type,
             price_per_serving, cuisine.
    """
    raise NotImplementedError("TODO: implement generate_meal_selections()")


def generate_discounts(df_activations: pd.DataFrame) -> pd.DataFrame:
    """
    TODO (Cursor): Build discount catalogue with usage stats.

    Start from DISCOUNT_CATALOGUE, then enrich with:
    - activations_used: count from df_activations
    - avg_activation_value: mean activation_value grouped by discount_code
    """
    raise NotImplementedError("TODO: implement generate_discounts()")


def generate_all(force: bool = False) -> dict[str, pd.DataFrame]:
    """
    Generate all datasets and write to OUTPUT_DIR as parquet.
    Skips generation if files already exist (unless force=True).
    Returns dict: {"sessions": df, "funnel_steps": df, "activations": df,
                   "meal_selections": df, "discounts": df}
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
    df_sessions.to_parquet(files["sessions"], index=False)

    print("Generating funnel steps...")
    df_funnel = generate_funnel_steps(df_sessions)
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
