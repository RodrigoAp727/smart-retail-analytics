"""Carga idempotente em PostgreSQL com upsert e SCD tipo 2."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import date, datetime, timedelta, timezone

import pandas as pd
from sqlalchemy import MetaData, Table, create_engine, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Connection, Engine

from config import Settings
from utils.logger import log_event


def create_db_engine(settings: Settings) -> Engine:
    """Cria engine SQLAlchemy para o banco do projeto."""
    return create_engine(settings.database_url, future=True)


def reflect_tables(engine: Engine, settings: Settings) -> dict[str, Table]:
    """Reflete as tabelas necessarias apos o bootstrap do schema."""
    metadata = MetaData(schema=settings.database_schema)
    table_names = ["etl_control", "dim_customer", "dim_product", "dim_time", "dim_store_channel", "fact_sales"]
    return {name: Table(name, metadata, autoload_with=engine) for name in table_names}


def _upsert_rows(connection: Connection, table: Table, rows: list[dict[str, object]], conflict_columns: list[str]) -> None:
    if not rows:
        return

    statement = insert(table).values(rows)
    excluded_columns = {
        column.name: getattr(statement.excluded, column.name)
        for column in table.columns
        if column.name not in conflict_columns and not column.primary_key
    }
    connection.execute(statement.on_conflict_do_update(index_elements=conflict_columns, set_=excluded_columns))


def _build_time_rows(sales: pd.DataFrame) -> list[dict[str, object]]:
    unique_dates = sales[["time_key", "sale_date"]].drop_duplicates().sort_values("sale_date")
    rows: list[dict[str, object]] = []
    for record in unique_dates.to_dict("records"):
        sale_date = pd.Timestamp(record["sale_date"])
        rows.append(
            {
                "time_key": int(record["time_key"]),
                "calendar_date": sale_date.date(),
                "year_number": sale_date.year,
                "quarter_number": sale_date.quarter,
                "month_number": sale_date.month,
                "month_name": sale_date.strftime("%B"),
                "day_number": sale_date.day,
            }
        )
    return rows


def _sync_customer_dimension(connection: Connection, table: Table, customers: pd.DataFrame) -> int:
    scd_changes = 0
    today = datetime.now(timezone.utc).date()
    for record in customers.to_dict("records"):
        current_row = connection.execute(
            select(table)
            .where(table.c.customer_id == record["customer_id"])
            .where(table.c.flag_current.is_(True))
        ).mappings().first()

        effective_date = record.get("effective_date") or today
        if isinstance(effective_date, pd.Timestamp):
            effective_date = effective_date.date()
        if isinstance(effective_date, datetime):
            effective_date = effective_date.date()

        candidate_payload = {
            "customer_id": record["customer_id"],
            "customer_name": record["customer_name"],
            "customer_segment": record["customer_segment"],
            "customer_region": record["customer_region"],
            "start_date": effective_date,
            "end_date": date(9999, 12, 31),
            "flag_current": True,
        }

        if current_row is None:
            connection.execute(insert(table).values(candidate_payload))
            scd_changes += 1
            continue

        has_change = any(
            current_row[column] != candidate_payload[column]
            for column in ("customer_name", "customer_segment", "customer_region")
        )
        if not has_change:
            continue

        connection.execute(
            update(table)
            .where(table.c.sk_customer == current_row["sk_customer"])
            .values(end_date=effective_date - timedelta(days=1), flag_current=False, updated_at=datetime.now(timezone.utc))
        )
        connection.execute(insert(table).values(candidate_payload))
        scd_changes += 1

    return scd_changes


def _build_customer_map(connection: Connection, table: Table) -> dict[str, int]:
    rows = connection.execute(
        select(table.c.customer_id, table.c.sk_customer).where(table.c.flag_current.is_(True))
    ).all()
    return {customer_id: sk_customer for customer_id, sk_customer in rows}


def _build_simple_map(connection: Connection, table: Table, business_key: str, surrogate_key: str) -> dict[str, int]:
    rows = connection.execute(select(getattr(table.c, business_key), getattr(table.c, surrogate_key))).all()
    return {business_value: surrogate_value for business_value, surrogate_value in rows}


def _upsert_control_records(
    connection: Connection,
    table: Table,
    source_files: Iterable[str],
    source_months: Iterable[str],
    load_mode: str,
    rows_loaded: int,
) -> None:
    load_timestamp = datetime.now(timezone.utc)
    rows = []
    for source_file, source_month in zip(source_files, source_months, strict=False):
        rows.append(
            {
                "source_file": source_file,
                "source_month": pd.Period(source_month, freq="M").to_timestamp().date(),
                "load_mode": load_mode,
                "load_timestamp": load_timestamp,
                "rows_loaded": rows_loaded,
                "status": "SUCCESS",
            }
        )

    _upsert_rows(connection, table, rows, ["source_file"])


def load_dataframes(
    engine: Engine,
    settings: Settings,
    customers: pd.DataFrame,
    products: pd.DataFrame,
    stores: pd.DataFrame,
    sales: pd.DataFrame,
    load_mode: str,
    logger: logging.Logger,
) -> dict[str, int]:
    """Carrega dimensoes e fato usando SQLAlchemy Core."""
    tables = reflect_tables(engine=engine, settings=settings)
    if sales.empty:
        log_event(logger, "No new sales files found", load_mode=load_mode)
        return {"rows_loaded": 0, "scd_changes": 0}

    with engine.begin() as connection:
        scd_changes = _sync_customer_dimension(connection, tables["dim_customer"], customers)

        _upsert_rows(
            connection,
            tables["dim_product"],
            products.to_dict("records"),
            ["product_id"],
        )
        _upsert_rows(
            connection,
            tables["dim_store_channel"],
            stores.to_dict("records"),
            ["store_id"],
        )
        _upsert_rows(connection, tables["dim_time"], _build_time_rows(sales), ["time_key"])

        customer_map = _build_customer_map(connection, tables["dim_customer"])
        product_map = _build_simple_map(connection, tables["dim_product"], "product_id", "sk_product")
        store_map = _build_simple_map(connection, tables["dim_store_channel"], "store_id", "sk_store_channel")

        fact_rows: list[dict[str, object]] = []
        for record in sales.to_dict("records"):
            fact_rows.append(
                {
                    "sale_id": record["sale_id"],
                    "time_key": int(record["time_key"]),
                    "sk_customer": customer_map[record["customer_id"]],
                    "sk_product": product_map[record["product_id"]],
                    "sk_store_channel": store_map[record["store_id"]],
                    "quantity": float(record["quantity"]),
                    "unit_cost": float(record["unit_cost"]),
                    "unit_price": float(record["unit_price"]),
                    "discount_amount": float(record["discount_amount"]),
                    "shipping_cost": float(record["shipping_cost"]),
                    "gross_revenue": float(record["gross_revenue"]),
                    "net_revenue": float(record["net_revenue"]),
                    "profit_margin": float(record["profit_margin"]),
                    "profit_margin_pct": float(record["profit_margin_pct"]),
                    "avg_ticket_line": float(record["avg_ticket_line"]),
                    "source_file": record["source_file"],
                }
            )

        _upsert_rows(connection, tables["fact_sales"], fact_rows, ["sale_id"])
        _upsert_control_records(
            connection,
            tables["etl_control"],
            source_files=sales["source_file"].drop_duplicates().tolist(),
            source_months=sales["source_month"].drop_duplicates().tolist(),
            load_mode=load_mode,
            rows_loaded=len(fact_rows),
        )

    log_event(logger, "Load completed", rows_loaded=len(sales), scd_changes=scd_changes)
    return {"rows_loaded": len(sales), "scd_changes": scd_changes}