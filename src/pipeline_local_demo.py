"""Pipeline local de contingencia sem Docker/PostgreSQL.

Este modo permite demonstrar o fluxo completo de dados (geracao, extracao,
transformacao e camada analitica) quando o ambiente nao suporta virtualizacao.
"""

from __future__ import annotations

import argparse
import json

import pandas as pd
from sqlalchemy import create_engine

from config import get_settings
from extract.extract import extract_datasets
from generator.generate_fake_data import generate_datasets
from transform.transform import transform_sales_dataframe
from utils.logger import get_logger, log_event


def _build_monthly_metrics(transformed_sales: pd.DataFrame) -> pd.DataFrame:
    """Gera metricas mensais para validacao rapida no portfolio."""
    grouped = (
        transformed_sales.groupby("sale_month", dropna=False)
        .agg(
            orders=("sale_id", "nunique"),
            net_revenue=("net_revenue", "sum"),
            gross_revenue=("gross_revenue", "sum"),
            profit_margin=("profit_margin", "sum"),
            avg_ticket_line=("avg_ticket_line", "mean"),
        )
        .reset_index()
        .sort_values("sale_month")
    )

    grouped["mom_growth"] = grouped["net_revenue"].diff()
    grouped["yoy_growth"] = grouped["net_revenue"].diff(12)
    grouped["profit_margin_pct"] = grouped["profit_margin"].div(
        grouped["net_revenue"].where(grouped["net_revenue"] != 0)
    ).fillna(0)
    return grouped


def _build_customer_abc(transformed_sales: pd.DataFrame) -> pd.DataFrame:
    """Calcula curva ABC de clientes em dataframe pronto para CSV."""
    abc = (
        transformed_sales.groupby(["customer_id", "customer_name"], dropna=False)
        .agg(net_revenue=("net_revenue", "sum"))
        .reset_index()
        .sort_values("net_revenue", ascending=False)
    )
    abc["cumulative_revenue"] = abc["net_revenue"].cumsum()
    total_revenue = abc["net_revenue"].sum()
    abc["cumulative_pct"] = abc["cumulative_revenue"].div(total_revenue if total_revenue else 1)
    abc["abc_class"] = pd.cut(
        abc["cumulative_pct"],
        bins=[-0.001, 0.8, 0.95, 1.0],
        labels=["A", "B", "C"],
    )
    return abc


def run_local_demo(regenerate_data: bool) -> dict[str, object]:
    """Executa pipeline local sem banco relacional externo."""
    settings = get_settings()
    logger = get_logger("smart_retail.local_demo", json_logs=settings.log_json)

    if regenerate_data:
        artifacts = generate_datasets(raw_dir=settings.raw_data_path, sample_dir=settings.sample_data_path)
        log_event(logger, "Synthetic data regenerated", sales_files=len(artifacts.sales_files))

    noop_engine = create_engine("sqlite://", future=True)
    extracted = extract_datasets(settings=settings, mode="full", engine=noop_engine, logger=logger)
    transformed = transform_sales_dataframe(extracted.sales)

    processed_dir = settings.project_root / "data" / "processed"
    marts_dir = settings.project_root / "data" / "marts"
    processed_dir.mkdir(parents=True, exist_ok=True)
    marts_dir.mkdir(parents=True, exist_ok=True)

    transformed_output = processed_dir / "sales_transformed.csv"
    transformed.to_csv(transformed_output, index=False)

    monthly_metrics = _build_monthly_metrics(transformed)
    customer_abc = _build_customer_abc(transformed)

    monthly_output = marts_dir / "monthly_metrics.csv"
    abc_output = marts_dir / "customer_abc.csv"
    monthly_metrics.to_csv(monthly_output, index=False)
    customer_abc.to_csv(abc_output, index=False)

    summary = {
        "rows_extracted": len(extracted.sales),
        "rows_transformed": len(transformed),
        "files_processed": len(extracted.processed_files),
        "total_net_revenue": float(round(transformed["net_revenue"].sum(), 2)),
        "avg_profit_margin_pct": float(round(transformed["profit_margin_pct"].mean(), 4)),
        "transformed_file": str(transformed_output.relative_to(settings.project_root)),
        "monthly_metrics_file": str(monthly_output.relative_to(settings.project_root)),
        "customer_abc_file": str(abc_output.relative_to(settings.project_root)),
    }

    summary_output = marts_dir / "run_summary.json"
    summary_output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log_event(logger, "Local demo completed", **summary)
    return summary


def main() -> None:
    """CLI do pipeline local para modo emergencia sem Docker."""
    parser = argparse.ArgumentParser(description="Run local ETL demo without Docker/PostgreSQL")
    parser.add_argument(
        "--regenerate-data",
        action="store_true",
        help="Regenera os CSVs sinteticos antes de executar extract/transform.",
    )
    args = parser.parse_args()

    summary = run_local_demo(regenerate_data=args.regenerate_data)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()