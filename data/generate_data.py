"""Generate a synthetic sales dataset for the MVP.

Run once (or whenever you want fresh data):
    python data/generate_data.py

Output: data/raw/sales.parquet
"""

from pathlib import Path

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
    fake = Faker()
    Faker.seed(SEED)
    rng = pd.np if hasattr(pd, "np") else __import__("numpy")
    rng.random.seed(SEED)

    dates = pd.date_range("2024-01-01", "2025-12-31", freq="D")

    rows = []
    for _ in range(NUM_ROWS):
        product = rng.random.choice(PRODUCTS)
        quantity = int(rng.random.randint(1, 50))
        unit_price = round(rng.random.uniform(5.0, 500.0), 2)
        rows.append(
            {
                "order_date": rng.random.choice(dates),
                "region": rng.random.choice(REGIONS),
                "product": product,
                "channel": rng.random.choice(CHANNELS),
                "quantity": quantity,
                "unit_price": unit_price,
                "revenue": round(quantity * unit_price, 2),
                "customer_name": fake.name(),
            }
        )

    df = pd.DataFrame(rows)
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
