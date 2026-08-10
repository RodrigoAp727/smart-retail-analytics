"""Regras de transformacao do pipeline de vendas.

Este modulo concentra funcoes puras para facilitar testes unitarios,
reuso no pipeline e clareza nas regras de negocio.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

REQUIRED_COLUMNS: tuple[str, ...] = (
    "sale_id",
    "sale_date",
    "customer_id",
    "customer_segment",
    "customer_region",
    "product_id",
    "product_name",
    "store_id",
    "store_channel",
    "store_region",
    "quantity",
    "unit_cost",
    "unit_price",
    "discount_amount",
    "shipping_cost",
    "customer_name",
    "product_category",
    "product_subcategory",
)


def _normalize_text(value: object, fallback: str = "Unknown") -> str:
    """Padroniza textos com trim, title case e fallback previsivel."""
    if value is None:
        return fallback

    text = str(value).strip()
    if not text:
        return fallback
    return text.title()


def _ensure_columns(dataframe: pd.DataFrame, columns: Iterable[str]) -> None:
    """Garante que o dataframe contenha todas as colunas exigidas."""
    missing_columns = [column for column in columns if column not in dataframe.columns]
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required columns: {missing}")


def transform_sales_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Aplica as regras de qualidade e enriquecimento nos dados de vendas.

    Estrategia para nulos:
    - nomes, categoria e subcategoria recebem fallback controlado;
    - desconto e frete nulos viram zero;
    - quantidade nula ou invalida vira 1;
    - custo nulo herda 70% do preco para evitar descartar a linha.
    """
    _ensure_columns(dataframe, REQUIRED_COLUMNS)

    transformed = dataframe.copy()

    transformed["sale_date"] = pd.to_datetime(transformed["sale_date"], errors="coerce")
    transformed["quantity"] = pd.to_numeric(transformed["quantity"], errors="coerce").fillna(1).clip(lower=1)
    transformed["unit_price"] = pd.to_numeric(transformed["unit_price"], errors="coerce")
    transformed["unit_cost"] = pd.to_numeric(transformed["unit_cost"], errors="coerce")
    transformed["discount_amount"] = pd.to_numeric(
        transformed["discount_amount"], errors="coerce"
    ).fillna(0)
    transformed["shipping_cost"] = pd.to_numeric(
        transformed["shipping_cost"], errors="coerce"
    ).fillna(0)

    transformed["unit_price"] = transformed["unit_price"].fillna(0).clip(lower=0)
    transformed["unit_cost"] = transformed["unit_cost"].fillna(transformed["unit_price"] * 0.7).clip(lower=0)

    transformed["customer_name"] = transformed["customer_name"].map(_normalize_text)
    transformed["product_category"] = transformed["product_category"].map(
        lambda value: _normalize_text(value, fallback="Uncategorized")
    )
    transformed["product_subcategory"] = transformed["product_subcategory"].map(
        lambda value: _normalize_text(value, fallback="General")
    )
    transformed["customer_segment"] = transformed["customer_segment"].map(
        lambda value: _normalize_text(value, fallback="Retail")
    )
    transformed["customer_region"] = transformed["customer_region"].map(
        lambda value: _normalize_text(value, fallback="Southeast")
    )
    transformed["product_name"] = transformed["product_name"].map(
        lambda value: _normalize_text(value, fallback="Unknown Product")
    )
    transformed["store_channel"] = transformed["store_channel"].map(
        lambda value: _normalize_text(value, fallback="Online")
    )
    transformed["store_region"] = transformed["store_region"].map(
        lambda value: _normalize_text(value, fallback="Southeast")
    )

    gross_revenue = transformed["quantity"] * transformed["unit_price"]
    net_revenue = gross_revenue - transformed["discount_amount"] + transformed["shipping_cost"]
    total_cost = transformed["quantity"] * transformed["unit_cost"]

    transformed["gross_revenue"] = gross_revenue.round(2)
    transformed["net_revenue"] = net_revenue.round(2)
    transformed["profit_margin"] = (net_revenue - total_cost).round(2)
    transformed["profit_margin_pct"] = (
        transformed["profit_margin"].div(net_revenue.where(net_revenue != 0)).fillna(0).round(4)
    )
    transformed["avg_ticket_line"] = (
        net_revenue.div(transformed["quantity"].where(transformed["quantity"] != 0)).fillna(0).round(2)
    )

    transformed["sale_month"] = transformed["sale_date"].dt.to_period("M").astype("string")
    transformed["sale_year"] = transformed["sale_date"].dt.year
    transformed["sale_month_number"] = transformed["sale_date"].dt.month
    transformed["sale_day"] = transformed["sale_date"].dt.day
    transformed["time_key"] = transformed["sale_date"].dt.strftime("%Y%m%d").astype("Int64")
    transformed["processed_at"] = pd.Timestamp.utcnow()

    return transformed