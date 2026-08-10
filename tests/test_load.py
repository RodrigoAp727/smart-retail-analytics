"""Testes de carga idempotente e SCD tipo 2."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from config import Settings
from load.load import load_dataframes
from pipeline_main import bootstrap_database
from transform.transform import transform_sales_dataframe


def _build_settings(database_url: str) -> Settings:
    return Settings(
        DATABASE_URL=database_url,
        DATABASE_SCHEMA="analytics",
    )


@pytest.fixture()
def postgres_engine() -> tuple[object, Settings]:
    database_url = "postgresql+psycopg://postgres:postgres@localhost:5432/smart_retail_test"
    engine = create_engine(database_url, future=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        pytest.skip(f"Postgres not available for integration test: {exc}")

    settings = _build_settings(database_url)
    bootstrap_database(engine=engine, project_root=Path(__file__).resolve().parents[1])
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE analytics.fact_sales RESTART IDENTITY CASCADE"))
        connection.execute(text("TRUNCATE TABLE analytics.dim_customer RESTART IDENTITY CASCADE"))
        connection.execute(text("TRUNCATE TABLE analytics.dim_product RESTART IDENTITY CASCADE"))
        connection.execute(text("TRUNCATE TABLE analytics.dim_store_channel RESTART IDENTITY CASCADE"))
        connection.execute(text("TRUNCATE TABLE analytics.dim_time RESTART IDENTITY CASCADE"))
        connection.execute(text("TRUNCATE TABLE analytics.etl_control RESTART IDENTITY CASCADE"))

    yield engine, settings
    engine.dispose()


def _build_dimensions() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    customers = pd.DataFrame(
        [
            {
                "customer_id": "C0001",
                "customer_name": "Maria Silva",
                "customer_segment": "Varejo",
                "customer_region": "Sudeste",
            }
        ]
    )
    products = pd.DataFrame(
        [
            {
                "product_id": "P0001",
                "product_name": "Mobile Item 001",
                "product_category": "Electronics",
                "product_subcategory": "Mobile",
                "unit_cost": 100.0,
                "unit_price": 160.0,
            }
        ]
    )
    stores = pd.DataFrame(
        [
            {
                "store_id": "ST001",
                "store_name": "Store 01",
                "store_channel": "Online",
                "store_region": "Sudeste",
            }
        ]
    )
    return customers, products, stores


def _build_sales_frame(customer_segment: str = "Varejo") -> pd.DataFrame:
    frame = pd.DataFrame(
        [
            {
                "sale_id": "S000001",
                "sale_date": "2024-01-15",
                "customer_id": "C0001",
                "customer_name": "Maria Silva",
                "customer_segment": customer_segment,
                "customer_region": "Sudeste",
                "product_id": "P0001",
                "product_name": "Mobile Item 001",
                "product_category": "Electronics",
                "product_subcategory": "Mobile",
                "store_id": "ST001",
                "store_channel": "Online",
                "store_region": "Sudeste",
                "quantity": 2,
                "unit_cost": 100.0,
                "unit_price": 160.0,
                "discount_amount": 10.0,
                "shipping_cost": 15.0,
                "source_file": "vendas_2024_01.csv",
                "source_month": "2024-01",
            }
        ]
    )
    return transform_sales_dataframe(frame)


def test_load_is_idempotent(postgres_engine: tuple[object, Settings]) -> None:
    engine, settings = postgres_engine
    customers, products, stores = _build_dimensions()
    sales = _build_sales_frame()

    first_run = load_dataframes(engine, settings, customers, products, stores, sales, "full", logging.getLogger("test"))
    second_run = load_dataframes(engine, settings, customers, products, stores, sales, "full", logging.getLogger("test"))

    with engine.connect() as connection:
        fact_count = connection.execute(text("SELECT COUNT(*) FROM analytics.fact_sales")).scalar_one()
        control_count = connection.execute(text("SELECT COUNT(*) FROM analytics.etl_control")).scalar_one()

    assert first_run["rows_loaded"] == 1
    assert second_run["rows_loaded"] == 1
    assert fact_count == 1
    assert control_count == 1


def test_load_applies_scd_type_2_for_customer_changes(postgres_engine: tuple[object, Settings]) -> None:
    engine, settings = postgres_engine
    customers, products, stores = _build_dimensions()
    sales = _build_sales_frame()

    load_dataframes(engine, settings, customers, products, stores, sales, "full", logging.getLogger("test"))

    changed_customers = customers.copy()
    changed_customers.loc[0, "customer_segment"] = "Corporativo"

    load_dataframes(engine, settings, changed_customers, products, stores, sales, "incremental", logging.getLogger("test"))

    with engine.connect() as connection:
        total_rows = connection.execute(text("SELECT COUNT(*) FROM analytics.dim_customer")).scalar_one()
        current_rows = connection.execute(
            text("SELECT COUNT(*) FROM analytics.dim_customer WHERE flag_current = TRUE")
        ).scalar_one()
        current_segment = connection.execute(
            text("SELECT customer_segment FROM analytics.dim_customer WHERE flag_current = TRUE")
        ).scalar_one()

    assert total_rows == 2
    assert current_rows == 1
    assert current_segment == "Corporativo"