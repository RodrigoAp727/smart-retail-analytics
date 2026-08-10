"""Extracao e validacao inicial dos arquivos CSV de origem."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from config import Settings
from utils.logger import log_event

SALES_COLUMNS: tuple[str, ...] = (
    "sale_id",
    "sale_date",
    "customer_id",
    "customer_name",
    "customer_segment",
    "customer_region",
    "product_id",
    "product_name",
    "product_category",
    "product_subcategory",
    "store_id",
    "store_channel",
    "store_region",
    "quantity",
    "unit_cost",
    "unit_price",
    "discount_amount",
    "shipping_cost",
)
CUSTOMER_COLUMNS: tuple[str, ...] = ("customer_id", "customer_name", "customer_segment", "customer_region")
PRODUCT_COLUMNS: tuple[str, ...] = (
    "product_id",
    "product_name",
    "product_category",
    "product_subcategory",
    "unit_cost",
    "unit_price",
)
STORE_COLUMNS: tuple[str, ...] = ("store_id", "store_name", "store_channel", "store_region")


@dataclass(slots=True)
class ExtractResult:
    """Agrupa os dados extraidos e os arquivos considerados na carga."""

    customers: pd.DataFrame
    products: pd.DataFrame
    stores: pd.DataFrame
    sales: pd.DataFrame
    processed_files: list[Path]


def _ensure_columns(dataframe: pd.DataFrame, required_columns: tuple[str, ...], dataset_name: str) -> None:
    missing = sorted(set(required_columns) - set(dataframe.columns))
    if missing:
        raise ValueError(f"Dataset {dataset_name} is missing columns: {', '.join(missing)}")


def _parse_sales_month(file_path: Path) -> pd.Timestamp:
    month_token = file_path.stem.replace("vendas_", "")
    return pd.Period(month_token.replace("_", "-"), freq="M").to_timestamp()


def _get_last_loaded_month(engine: Engine, settings: Settings) -> pd.Timestamp | None:
    query = text(
        f"""
        SELECT MAX(source_month) AS latest_month
        FROM {settings.database_schema}.etl_control
        WHERE status = 'SUCCESS'
        """
    )
    try:
        with engine.connect() as connection:
            latest_month = connection.execute(query).scalar_one_or_none()
            if latest_month is None:
                return None
            return pd.Timestamp(latest_month)
    except SQLAlchemyError:
        return None


def _select_sales_files(raw_data_path: Path, mode: str, engine: Engine, settings: Settings) -> list[Path]:
    sales_files = sorted(raw_data_path.glob("vendas_*.csv"))
    if mode == "full":
        return sales_files

    latest_loaded_month = _get_last_loaded_month(engine=engine, settings=settings)
    if latest_loaded_month is None:
        return sales_files

    return [file_path for file_path in sales_files if _parse_sales_month(file_path) > latest_loaded_month]


def extract_datasets(settings: Settings, mode: str, engine: Engine, logger: logging.Logger) -> ExtractResult:
    """Extrai os arquivos de clientes, produtos, lojas e vendas."""
    raw_data_path = settings.raw_data_path
    customer_file = raw_data_path / "customers.csv"
    product_file = raw_data_path / "products.csv"
    store_file = raw_data_path / "stores.csv"

    customers = pd.read_csv(customer_file)
    products = pd.read_csv(product_file)
    stores = pd.read_csv(store_file)

    _ensure_columns(customers, CUSTOMER_COLUMNS, "customers")
    _ensure_columns(products, PRODUCT_COLUMNS, "products")
    _ensure_columns(stores, STORE_COLUMNS, "stores")

    processed_files = _select_sales_files(raw_data_path=raw_data_path, mode=mode, engine=engine, settings=settings)
    sales_frames: list[pd.DataFrame] = []
    for file_path in processed_files:
        frame = pd.read_csv(file_path)
        _ensure_columns(frame, SALES_COLUMNS, file_path.name)
        frame["source_file"] = file_path.name
        frame["source_month"] = str(_parse_sales_month(file_path).to_period("M"))
        sales_frames.append(frame)

    sales = pd.concat(sales_frames, ignore_index=True) if sales_frames else pd.DataFrame(columns=[*SALES_COLUMNS, "source_file", "source_month"])

    log_event(
        logger,
        "Extract completed",
        customers_rows=len(customers),
        products_rows=len(products),
        stores_rows=len(stores),
        sales_rows=len(sales),
        processed_files=len(processed_files),
    )
    return ExtractResult(customers=customers, products=products, stores=stores, sales=sales, processed_files=processed_files)