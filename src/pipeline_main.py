"""Orquestrador do pipeline ETL com CLI e metricas de execucao."""

from __future__ import annotations

import argparse
import time
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import text

from config import get_settings
from extract.extract import extract_datasets
from load.load import create_db_engine, load_dataframes
from transform.transform import transform_sales_dataframe
from utils.logger import get_logger, log_event


@contextmanager
def timed_stage(logger, stage_name: str):
    """Mede e registra o tempo de cada etapa do pipeline."""
    start_time = time.perf_counter()
    try:
        yield
    finally:
        elapsed = round(time.perf_counter() - start_time, 3)
        log_event(logger, f"Stage {stage_name} completed", stage=stage_name, elapsed_seconds=elapsed)


def _run_sql_file(engine, sql_file: Path) -> None:
    statements = sql_file.read_text(encoding="utf-8")
    with engine.begin() as connection:
        connection.execute(text(statements))


def bootstrap_database(engine, project_root: Path) -> None:
    """Executa os scripts DDL na ordem definida pelo projeto."""
    ddl_path = project_root / "database" / "ddl"
    for script_name in ("01_create_schema.sql", "02_create_dimensions.sql", "03_create_fact.sql"):
        _run_sql_file(engine, ddl_path / script_name)


def parse_args() -> argparse.Namespace:
    """Define os argumentos suportados pela CLI do pipeline."""
    parser = argparse.ArgumentParser(description="Smart Retail ETL pipeline")
    parser.add_argument("--mode", choices=["full", "incremental"], default="full")
    return parser.parse_args()


def main() -> None:
    """Executa bootstrap, extract, transform e load com rollback automatico."""
    args = parse_args()
    settings = get_settings()
    logger = get_logger("smart_retail.pipeline", json_logs=settings.log_json)
    engine = create_db_engine(settings)

    total_start_time = time.perf_counter()
    try:
        with timed_stage(logger, "bootstrap"):
            bootstrap_database(engine=engine, project_root=settings.project_root)

        with timed_stage(logger, "extract"):
            extracted = extract_datasets(settings=settings, mode=args.mode, engine=engine, logger=logger)

        with timed_stage(logger, "transform"):
            transformed_sales = transform_sales_dataframe(extracted.sales) if not extracted.sales.empty else extracted.sales

        with timed_stage(logger, "load"):
            load_stats = load_dataframes(
                engine=engine,
                settings=settings,
                customers=extracted.customers,
                products=extracted.products,
                stores=extracted.stores,
                sales=transformed_sales,
                load_mode=args.mode,
                logger=logger,
            )

        total_elapsed = round(time.perf_counter() - total_start_time, 3)
        log_event(
            logger,
            "Pipeline completed successfully",
            mode=args.mode,
            elapsed_seconds=total_elapsed,
            rows_loaded=load_stats["rows_loaded"],
            scd_changes=load_stats["scd_changes"],
        )
    except Exception:
        logger.exception("Pipeline execution failed")
        raise


if __name__ == "__main__":
    main()