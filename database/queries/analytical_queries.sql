-- Curva ABC de clientes com acumulado percentual.
WITH customer_revenue AS (
    SELECT
        dc.customer_id,
        dc.customer_name,
        SUM(fs.net_revenue) AS total_revenue
    FROM analytics.fact_sales fs
    JOIN analytics.dim_customer dc ON fs.sk_customer = dc.sk_customer
    GROUP BY dc.customer_id, dc.customer_name
),
customer_rank AS (
    SELECT
        customer_id,
        customer_name,
        total_revenue,
        SUM(total_revenue) OVER (ORDER BY total_revenue DESC) AS running_revenue,
        SUM(total_revenue) OVER () AS overall_revenue
    FROM customer_revenue
)
SELECT
    customer_id,
    customer_name,
    total_revenue,
    ROUND(running_revenue / NULLIF(overall_revenue, 0), 4) AS cumulative_pct,
    CASE
        WHEN running_revenue / NULLIF(overall_revenue, 0) <= 0.8 THEN 'A'
        WHEN running_revenue / NULLIF(overall_revenue, 0) <= 0.95 THEN 'B'
        ELSE 'C'
    END AS abc_class
FROM customer_rank;

-- Crescimento MoM e YoY por receita mensal.
WITH monthly_revenue AS (
    SELECT
        dt.year_number,
        dt.month_number,
        DATE_TRUNC('month', dt.calendar_date)::date AS month_start,
        SUM(fs.net_revenue) AS total_revenue
    FROM analytics.fact_sales fs
    JOIN analytics.dim_time dt ON fs.time_key = dt.time_key
    GROUP BY dt.year_number, dt.month_number, DATE_TRUNC('month', dt.calendar_date)
)
SELECT
    month_start,
    total_revenue,
    total_revenue - LAG(total_revenue) OVER (ORDER BY month_start) AS mom_growth,
    total_revenue - LAG(total_revenue, 12) OVER (ORDER BY month_start) AS yoy_growth
FROM monthly_revenue
ORDER BY month_start;

-- Multi-CTE para ranking de produtos por categoria.
WITH product_sales AS (
    SELECT
        dp.product_category,
        dp.product_subcategory,
        dp.product_name,
        SUM(fs.net_revenue) AS total_revenue,
        SUM(fs.quantity) AS total_units
    FROM analytics.fact_sales fs
    JOIN analytics.dim_product dp ON fs.sk_product = dp.sk_product
    GROUP BY dp.product_category, dp.product_subcategory, dp.product_name
),
category_totals AS (
    SELECT
        product_category,
        SUM(total_revenue) AS category_revenue
    FROM product_sales
    GROUP BY product_category
),
ranked_products AS (
    SELECT
        ps.product_category,
        ps.product_subcategory,
        ps.product_name,
        ps.total_revenue,
        ps.total_units,
        ct.category_revenue,
        DENSE_RANK() OVER (
            PARTITION BY ps.product_category
            ORDER BY ps.total_revenue DESC, ps.total_units DESC
        ) AS category_rank
    FROM product_sales ps
    JOIN category_totals ct ON ps.product_category = ct.product_category
)
SELECT *
FROM ranked_products
WHERE category_rank <= 5
ORDER BY product_category, category_rank, total_revenue DESC;