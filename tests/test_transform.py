"""Testes unitarios das regras de transformacao."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from generator.generate_fake_data import generate_datasets
from transform.transform import transform_sales_dataframe


def test_transform_sales_dataframe_applies_business_rules() -> None:
    source = pd.DataFrame(
        [
            {
                "sale_id": "S-1",
                "sale_date": "2024-02-15",
                "customer_id": "C-10",
                "customer_segment": None,
                "customer_region": None,
                "product_id": "P-99",
                "product_name": None,
                "store_id": "ST-7",
                "store_channel": None,
                "store_region": None,
                "quantity": None,
                "unit_cost": None,
                "unit_price": 200.0,
                "discount_amount": None,
                "shipping_cost": 10.0,
                "customer_name": "  maria silva  ",
                "product_category": None,
                "product_subcategory": "  smart devices ",
            }
        ]
    )

    transformed = transform_sales_dataframe(source)
    record = transformed.iloc[0]

    assert record["quantity"] == 1
    assert record["unit_cost"] == 140.0
    assert record["customer_name"] == "Maria Silva"
    assert record["customer_segment"] == "Retail"
    assert record["customer_region"] == "Southeast"
    assert record["product_name"] == "Unknown Product"
    assert record["store_channel"] == "Online"
    assert record["store_region"] == "Southeast"
    assert record["product_category"] == "Uncategorized"
    assert record["product_subcategory"] == "Smart Devices"
    assert record["net_revenue"] == 210.0
    assert record["profit_margin"] == 70.0
    assert record["profit_margin_pct"] == 0.3333
    assert record["avg_ticket_line"] == 210.0
    assert record["sale_month"] == "2024-02"


def test_transform_sales_dataframe_rejects_missing_columns() -> None:
    source = pd.DataFrame([{"sale_id": "S-2"}])

    try:
        transform_sales_dataframe(source)
    except ValueError as exc:
        assert "Missing required columns" in str(exc)
    else:
        raise AssertionError("Expected ValueError for incomplete schema")


def test_generate_datasets_creates_expected_files(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    sample_dir = tmp_path / "samples"

    generated = generate_datasets(raw_dir=raw_dir, sample_dir=sample_dir)

    assert len(generated.sales_files) == 24
    assert (raw_dir / "customers.csv").exists()
    assert (raw_dir / "products.csv").exists()
    assert (raw_dir / "stores.csv").exists()
    assert (sample_dir / "sales_sample.csv").exists()