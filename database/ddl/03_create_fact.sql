CREATE TABLE IF NOT EXISTS analytics.fact_sales (
    sk_sale BIGSERIAL PRIMARY KEY,
    sale_id VARCHAR(30) NOT NULL UNIQUE,
    time_key INTEGER NOT NULL REFERENCES analytics.dim_time (time_key),
    sk_customer BIGINT NOT NULL REFERENCES analytics.dim_customer (sk_customer),
    sk_product BIGINT NOT NULL REFERENCES analytics.dim_product (sk_product),
    sk_store_channel BIGINT NOT NULL REFERENCES analytics.dim_store_channel (sk_store_channel),
    quantity NUMERIC(12, 2) NOT NULL,
    unit_cost NUMERIC(12, 2) NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,
    discount_amount NUMERIC(12, 2) NOT NULL,
    shipping_cost NUMERIC(12, 2) NOT NULL,
    gross_revenue NUMERIC(14, 2) NOT NULL,
    net_revenue NUMERIC(14, 2) NOT NULL,
    profit_margin NUMERIC(14, 2) NOT NULL,
    profit_margin_pct NUMERIC(10, 4) NOT NULL,
    avg_ticket_line NUMERIC(14, 2) NOT NULL,
    source_file VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_fact_sales_customer_time
    ON analytics.fact_sales (sk_customer, time_key);

CREATE INDEX IF NOT EXISTS ix_fact_sales_product_time
    ON analytics.fact_sales (sk_product, time_key);

CREATE INDEX IF NOT EXISTS ix_fact_sales_store_time
    ON analytics.fact_sales (sk_store_channel, time_key);