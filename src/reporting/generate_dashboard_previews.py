"""Gera previews visuais de dashboard a partir dos dados processados locais.

Este modulo cria imagens PNG em dashboard/screenshots para apresentar o projeto
mesmo sem o arquivo Power BI final.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

BASE_DIR = Path(__file__).resolve().parents[2]
MARTS_DIR = BASE_DIR / "data" / "marts"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
SCREENSHOTS_DIR = BASE_DIR / "dashboard" / "screenshots"

CATEGORY_LABELS_PT = {
    "Office": "Escritorio",
    "Beauty": "Beleza",
    "Fashion": "Moda",
    "Home": "Casa",
    "Electronics": "Eletronicos",
}

CHANNEL_LABELS_PT = {
    "Physical": "Fisico",
    "Online": "Online",
}

REGION_LABELS_PT = {
    "North": "Norte",
    "Northeast": "Nordeste",
    "Midwest": "Centro-Oeste",
    "Southeast": "Sudeste",
    "South": "Sul",
}


def _translate_labels(values: list[str], mapping: dict[str, str]) -> list[str]:
    """Traduz labels de exibicao para portugues, mantendo valor original se nao houver mapeamento."""
    return [mapping.get(value, value) for value in values]


def _format_currency(value: float, _: int) -> str:
    """Formata valores monetarios em milhoes para facilitar leitura executiva."""
    return f"R$ {value / 1_000_000:,.1f} mi".replace(",", "X").replace(".", ",").replace("X", ".")


def _format_percent(value: float, _: int) -> str:
    """Formata eixo percentual de forma amigavel em portugues."""
    return f"{value:.0f}%"


def _load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    monthly = pd.read_csv(MARTS_DIR / "monthly_metrics.csv")
    abc = pd.read_csv(MARTS_DIR / "customer_abc.csv")
    sales = pd.read_csv(PROCESSED_DIR / "sales_transformed.csv")

    monthly["sale_month"] = pd.to_datetime(monthly["sale_month"], format="%Y-%m", errors="coerce")
    return monthly, abc, sales


def _save_figure(fig: plt.Figure, target_name: str) -> None:
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = SCREENSHOTS_DIR / target_name
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def create_executive_overview(monthly: pd.DataFrame) -> None:
    """Cria painel executivo com KPIs e tendencia mensal."""
    total_revenue = monthly["net_revenue"].sum()
    total_margin = monthly["profit_margin"].sum()
    avg_ticket = monthly["avg_ticket_line"].mean()
    yoy_latest = monthly["yoy_growth"].dropna().iloc[-1] if monthly["yoy_growth"].dropna().any() else 0

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    fig.suptitle("Visao Executiva", fontsize=20, fontweight="bold")

    kpis = [
        ("Receita Total", f"R$ {total_revenue:,.0f}"),
        ("Margem Total", f"R$ {total_margin:,.0f}"),
        ("Ticket Medio", f"R$ {avg_ticket:,.2f}"),
        ("Variacao YoY (ultimo mes)", f"R$ {yoy_latest:,.0f}"),
    ]
    for axis, (label, value) in zip(axes.flat, kpis, strict=False):
        axis.axis("off")
        axis.text(
            0.5,
            0.62,
            value.replace(",", "X").replace(".", ",").replace("X", "."),
            fontsize=24,
            fontweight="bold",
            ha="center",
        )
        axis.text(0.5, 0.36, label, fontsize=12, ha="center", color="#4f5b6b")

    _save_figure(fig, "executive-overview.png")


def create_monthly_trends(monthly: pd.DataFrame) -> None:
    """Cria linha temporal com receita e variacoes MoM/YoY."""
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax1 = plt.subplots(figsize=(14, 6))
    ax2 = ax1.twinx()

    ax1.plot(monthly["sale_month"], monthly["net_revenue"], color="#1f77b4", linewidth=2.8, label="Receita Liquida")
    ax2.bar(monthly["sale_month"], monthly["mom_growth"].fillna(0), alpha=0.32, color="#2ca02c", label="Variacao MoM")
    ax2.plot(monthly["sale_month"], monthly["yoy_growth"].fillna(0), color="#d62728", linewidth=2.1, label="Variacao YoY")

    ax1.set_title("Tendencia Mensal: Receita, MoM e YoY")
    ax1.set_xlabel("Mes")
    ax1.set_ylabel("Receita Liquida")
    ax2.set_ylabel("Variacao")
    ax1.yaxis.set_major_formatter(FuncFormatter(_format_currency))
    ax2.yaxis.set_major_formatter(FuncFormatter(_format_currency))

    handles_1, labels_1 = ax1.get_legend_handles_labels()
    handles_2, labels_2 = ax2.get_legend_handles_labels()
    ax1.legend(handles_1 + handles_2, labels_1 + labels_2, loc="upper left")

    _save_figure(fig, "monthly-trends.png")


def create_customer_abc(abc: pd.DataFrame) -> None:
    """Cria visual da curva ABC de clientes."""
    ordered = abc.copy()

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(range(1, len(ordered) + 1), ordered["cumulative_pct"] * 100, color="#003f5c", linewidth=2.5)
    ax.axhline(80, color="#2ca02c", linestyle="--", linewidth=1.5)
    ax.axhline(95, color="#ff7f0e", linestyle="--", linewidth=1.5)
    ax.fill_between(range(1, len(ordered) + 1), 0, ordered["cumulative_pct"] * 100, color="#a6cee3", alpha=0.35)

    ax.set_title("Curva ABC de Clientes")
    ax.set_xlabel("Clientes ordenados por receita")
    ax.set_ylabel("Receita acumulada")
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(FuncFormatter(_format_percent))

    _save_figure(fig, "customer-abc-analysis.png")


def create_operational_overview(sales: pd.DataFrame) -> None:
    """Cria painel operacional por categoria, regiao e canal."""
    category = (
        sales.groupby("product_category", dropna=False)["net_revenue"]
        .sum()
        .sort_values(ascending=False)
        .head(8)
    )
    channel = sales.groupby("store_channel", dropna=False)["net_revenue"].sum().sort_values(ascending=False)
    heatmap = (
        sales.pivot_table(
            index="customer_region",
            columns="product_category",
            values="net_revenue",
            aggfunc="sum",
            fill_value=0,
        )
        .sort_index()
    )

    category.index = _translate_labels(category.index.astype(str).tolist(), CATEGORY_LABELS_PT)
    channel.index = _translate_labels(channel.index.astype(str).tolist(), CHANNEL_LABELS_PT)
    heatmap = heatmap.rename(
        index=lambda value: REGION_LABELS_PT.get(str(value), str(value)),
        columns=lambda value: CATEGORY_LABELS_PT.get(str(value), str(value)),
    )

    plt.style.use("seaborn-v0_8-whitegrid")
    fig = plt.figure(figsize=(14, 8))
    grid = fig.add_gridspec(2, 2)
    ax1 = fig.add_subplot(grid[0, :])
    ax2 = fig.add_subplot(grid[1, 0])
    ax3 = fig.add_subplot(grid[1, 1])

    category.plot(kind="bar", ax=ax1, color="#4c78a8")
    ax1.set_title("Receita por Categoria de Produto")
    ax1.set_xlabel("")
    ax1.set_ylabel("Receita Liquida")
    ax1.yaxis.set_major_formatter(FuncFormatter(_format_currency))

    channel.plot(kind="bar", ax=ax2, color="#f58518")
    ax2.set_title("Receita por Canal")
    ax2.set_xlabel("")
    ax2.set_ylabel("Receita Liquida")
    ax2.yaxis.set_major_formatter(FuncFormatter(_format_currency))

    im = ax3.imshow(heatmap.values, aspect="auto", cmap="Blues")
    ax3.set_title("Mapa de Calor: Regiao x Categoria")
    ax3.set_xticks(range(len(heatmap.columns)))
    ax3.set_xticklabels(heatmap.columns, rotation=45, ha="right")
    ax3.set_yticks(range(len(heatmap.index)))
    ax3.set_yticklabels(heatmap.index)
    fig.colorbar(im, ax=ax3, fraction=0.046, pad=0.04)

    fig.suptitle("Visao Operacional", fontsize=18, fontweight="bold")
    _save_figure(fig, "operational-overview.png")


def main() -> None:
    """Executa a geracao de todos os previews de dashboard."""
    monthly, abc, sales = _load_inputs()
    create_executive_overview(monthly)
    create_monthly_trends(monthly)
    create_customer_abc(abc)
    create_operational_overview(sales)
    print("Imagens de preview do dashboard geradas em dashboard/screenshots")


if __name__ == "__main__":
    main()