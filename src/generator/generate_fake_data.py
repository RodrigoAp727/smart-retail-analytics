"""Gera dados 100% sinteticos para demonstracao de portfolio.

Os registros criados neste arquivo nao representam clientes, produtos,
lojas ou transacoes reais. O objetivo e permitir avaliacao tecnica do ETL,
modelo dimensional e dashboard sem expor dados sensiveis.
"""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import pandas as pd
from faker import Faker

SEED = 42
REGIONS = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]
SEGMENTS = ["Varejo", "Corporativo", "PME"]
CHANNELS = ["Online", "Physical"]


@dataclass(slots=True)
class GeneratedArtifacts:
    """Representa os caminhos dos arquivos sinteticos gerados."""

    customer_file: Path
    product_file: Path
    store_file: Path
    sales_files: list[Path]


def _build_customers(fake: Faker, rng: random.Random, total_customers: int = 500) -> pd.DataFrame:
    customers: list[dict[str, object]] = []
    for index in range(1, total_customers + 1):
        customers.append(
            {
                "customer_id": f"C{index:04d}",
                "customer_name": fake.name(),
                "customer_segment": rng.choices(SEGMENTS, weights=[0.55, 0.2, 0.25], k=1)[0],
                "customer_region": rng.choices(REGIONS, weights=[0.1, 0.18, 0.12, 0.4, 0.2], k=1)[0],
            }
        )
    return pd.DataFrame(customers)


def _build_products(rng: random.Random, total_products: int = 200) -> pd.DataFrame:
    taxonomy = {
        "Electronics": ["Mobile", "Notebook", "Smart Home", "Gaming"],
        "Home": ["Kitchen", "Furniture", "Decor", "Utilities"],
        "Fashion": ["Accessories", "Shoes", "Apparel", "Sportswear"],
        "Office": ["Stationery", "Printing", "Ergonomics", "Storage"],
        "Beauty": ["Skincare", "Haircare", "Makeup", "Fragrance"],
    }
    products: list[dict[str, object]] = []
    for index in range(1, total_products + 1):
        category = rng.choice(list(taxonomy.keys()))
        subcategory = rng.choice(taxonomy[category])
        unit_cost = round(rng.uniform(12, 650), 2)
        margin_multiplier = rng.uniform(1.15, 1.85)
        products.append(
            {
                "product_id": f"P{index:04d}",
                "product_name": f"{subcategory} Item {index:03d}",
                "product_category": category,
                "product_subcategory": subcategory,
                "unit_cost": unit_cost,
                "unit_price": round(unit_cost * margin_multiplier, 2),
            }
        )
    return pd.DataFrame(products)


def _build_stores(rng: random.Random, total_stores: int = 15) -> pd.DataFrame:
    stores: list[dict[str, object]] = []
    for index in range(1, total_stores + 1):
        channel = "Online" if index <= 3 else "Physical"
        stores.append(
            {
                "store_id": f"ST{index:03d}",
                "store_name": f"Store {index:02d}",
                "store_channel": channel,
                "store_region": rng.choices(REGIONS, weights=[0.08, 0.16, 0.1, 0.46, 0.2], k=1)[0],
            }
        )
    return pd.DataFrame(stores)


def _build_sales(
    customers: pd.DataFrame,
    products: pd.DataFrame,
    stores: pd.DataFrame,
    rng: random.Random,
    total_sales: int = 20_000,
) -> pd.DataFrame:
    sale_rows: list[dict[str, object]] = []
    month_starts = pd.date_range("2024-01-01", periods=24, freq="MS")
    month_weights = [1.0] * 24
    for index, month_start in enumerate(month_starts):
        if month_start.month in {11, 12}:
            month_weights[index] = 2.4
        elif month_start.month in {6, 7}:
            month_weights[index] = 0.85

    for sale_number in range(1, total_sales + 1):
        month_start = rng.choices(list(month_starts), weights=month_weights, k=1)[0]
        month_end = (month_start + pd.offsets.MonthEnd(0)).to_pydatetime()
        sale_date = month_start.to_pydatetime() + timedelta(days=rng.randint(0, month_end.day - 1))
        customer = customers.sample(1, random_state=SEED + sale_number).iloc[0]
        product = products.sample(1, random_state=SEED * 2 + sale_number).iloc[0]
        store = stores.sample(1, random_state=SEED * 3 + sale_number).iloc[0]

        quantity = rng.choices([1, 2, 3, 4, 5, 8, 12, None], weights=[35, 24, 16, 10, 6, 4, 1, 4], k=1)[0]
        if rng.random() < 0.01:
            quantity = rng.randint(40, 120)

        unit_price = float(product["unit_price"])
        unit_cost = float(product["unit_cost"])
        if rng.random() < 0.02:
            unit_price = round(unit_price * rng.uniform(2.5, 5.0), 2)

        discount_amount = round(unit_price * rng.uniform(0, 0.2), 2) if rng.random() < 0.35 else 0.0
        shipping_cost = round(rng.uniform(0, 45), 2) if store["store_channel"] == "Online" else 0.0

        sale_rows.append(
            {
                "sale_id": f"S{sale_number:06d}",
                "sale_date": sale_date.strftime("%Y-%m-%d"),
                "customer_id": customer["customer_id"],
                "customer_name": customer["customer_name"],
                "customer_segment": customer["customer_segment"],
                "customer_region": customer["customer_region"],
                "product_id": product["product_id"],
                "product_name": product["product_name"],
                "product_category": product["product_category"],
                "product_subcategory": product["product_subcategory"],
                "store_id": store["store_id"],
                "store_channel": store["store_channel"],
                "store_region": store["store_region"],
                "quantity": quantity,
                "unit_cost": None if rng.random() < 0.03 else unit_cost,
                "unit_price": None if rng.random() < 0.01 else unit_price,
                "discount_amount": None if rng.random() < 0.05 else discount_amount,
                "shipping_cost": None if rng.random() < 0.04 else shipping_cost,
            }
        )

    return pd.DataFrame(sale_rows)


def generate_datasets(raw_dir: Path, sample_dir: Path) -> GeneratedArtifacts:
    """Gera datasets sintéticos e grava CSVs particionados por mes."""
    fake = Faker("pt_BR")
    Faker.seed(SEED)
    rng = random.Random(SEED)

    raw_dir.mkdir(parents=True, exist_ok=True)
    sample_dir.mkdir(parents=True, exist_ok=True)

    customers = _build_customers(fake=fake, rng=rng)
    products = _build_products(rng=rng)
    stores = _build_stores(rng=rng)
    sales = _build_sales(customers=customers, products=products, stores=stores, rng=rng)

    customer_file = raw_dir / "customers.csv"
    product_file = raw_dir / "products.csv"
    store_file = raw_dir / "stores.csv"

    customers.to_csv(customer_file, index=False)
    products.to_csv(product_file, index=False)
    stores.to_csv(store_file, index=False)

    sales_files: list[Path] = []
    sales["sale_month"] = pd.to_datetime(sales["sale_date"]).dt.to_period("M")
    for sale_month, monthly_frame in sales.groupby("sale_month"):
        month_key = str(sale_month).replace("-", "_")
        target_file = raw_dir / f"vendas_{month_key}.csv"
        monthly_frame.drop(columns=["sale_month"]).to_csv(target_file, index=False)
        sales_files.append(target_file)

    customers.head(10).to_csv(sample_dir / "customers_sample.csv", index=False)
    products.head(10).to_csv(sample_dir / "products_sample.csv", index=False)
    sales.head(25).drop(columns=["sale_month"]).to_csv(sample_dir / "sales_sample.csv", index=False)

    return GeneratedArtifacts(
        customer_file=customer_file,
        product_file=product_file,
        store_file=store_file,
        sales_files=sorted(sales_files),
    )


def main() -> None:
    """Executa a geracao de dados sinteticos via CLI."""
    parser = argparse.ArgumentParser(description="Generate synthetic smart retail data")
    parser.add_argument("--output-dir", default="data/raw", help="Diretorio dos CSVs brutos")
    parser.add_argument("--sample-dir", default="data/samples", help="Diretorio das amostras versionadas")
    args = parser.parse_args()

    artifacts = generate_datasets(raw_dir=Path(args.output_dir), sample_dir=Path(args.sample_dir))
    print(f"Generated {len(artifacts.sales_files)} monthly sales files in {args.output_dir}")


if __name__ == "__main__":
    main()