"""Generate a synthetic sales dataset for the MVP.

Run once (or whenever you want fresh data):
    python data/generate_data.py

Output: data/raw/sales.parquet
"""

from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

SEED = 42
NUM_ROWS = 30_000
OUTPUT_DIR = Path(__file__).resolve().parent / "raw"

REGIONS = ["North America", "Europe", "Asia Pacific", "Latin America"]
PRODUCTS = [
    "Widget A",
    "Widget B",
    "Gadget Pro",
    "Gadget Lite",
    "Service Plan S",
    "Service Plan M",
    "Service Plan L",
]
CHANNELS = ["Online", "Retail", "Partner"]


def generate() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    fake = Faker()
    Faker.seed(SEED)

    dates = pd.date_range("2024-01-01", "2025-12-31", freq="D")
    n = NUM_ROWS

    date_idx = rng.integers(0, len(dates), size=n)
    region_idx = rng.integers(0, len(REGIONS), size=n)
    product_idx = rng.integers(0, len(PRODUCTS), size=n)
    channel_idx = rng.integers(0, len(CHANNELS), size=n)
    quantities = rng.integers(1, 51, size=n)
    unit_prices = np.round(rng.uniform(5.0, 500.0, size=n), 2)

    df = pd.DataFrame(
        {
            "order_date": dates[date_idx],
            "region": np.array(REGIONS)[region_idx],
            "product": np.array(PRODUCTS)[product_idx],
            "channel": np.array(CHANNELS)[channel_idx],
            "quantity": quantities,
            "unit_price": unit_prices,
            "revenue": np.round(quantities * unit_prices, 2),
            "customer_name": [fake.name() for _ in range(n)],
        }
    )
    df["order_date"] = pd.to_datetime(df["order_date"])
    return df.sort_values("order_date").reset_index(drop=True)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = generate()
    out_path = OUTPUT_DIR / "sales.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Generated {len(df):,} rows -> {out_path}")


if __name__ == "__main__":
    main()
