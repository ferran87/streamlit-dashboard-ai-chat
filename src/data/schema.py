"""Column definitions and descriptions for the sales dataset.

Single source of truth: used by the dashboard, the metrics layer,
and the AI chat context builder.
"""

SCHEMA = {
    "order_date": {
        "dtype": "datetime64[ns]",
        "description": "Date the order was placed",
    },
    "region": {
        "dtype": "category",
        "description": "Sales region (North America, Europe, Asia Pacific, Latin America)",
    },
    "product": {
        "dtype": "category",
        "description": "Product name",
    },
    "channel": {
        "dtype": "category",
        "description": "Sales channel (Online, Retail, Partner)",
    },
    "quantity": {
        "dtype": "int64",
        "description": "Number of units sold",
    },
    "unit_price": {
        "dtype": "float64",
        "description": "Price per unit in USD",
    },
    "revenue": {
        "dtype": "float64",
        "description": "Total order revenue in USD (quantity * unit_price)",
    },
    "customer_name": {
        "dtype": "object",
        "description": "Customer full name (synthetic)",
    },
}

TABLE_NAME = "sales"
TABLE_DESCRIPTION = (
    "Synthetic sales transactions spanning 2024-01-01 to 2025-12-31. "
    "Each row represents a single order line."
)


def schema_as_text() -> str:
    """Return a human/LLM-readable summary of the schema."""
    lines = [f"Table: {TABLE_NAME}", f"Description: {TABLE_DESCRIPTION}", "", "Columns:"]
    for col, meta in SCHEMA.items():
        lines.append(f"  - {col} ({meta['dtype']}): {meta['description']}")
    return "\n".join(lines)
