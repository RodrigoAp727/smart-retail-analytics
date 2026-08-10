CREATE TABLE IF NOT EXISTS analytics.dim_customer (
    sk_customer BIGSERIAL PRIMARY KEY,
    customer_id VARCHAR(20) NOT NULL,
    customer_name VARCHAR(200) NOT NULL,
    customer_segment VARCHAR(50) NOT NULL,
    customer_region VARCHAR(50) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL DEFAULT DATE '9999-12-31',
    flag_current BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_dim_customer_current
    ON analytics.dim_customer (customer_id, flag_current)
    WHERE flag_current = TRUE;

CREATE INDEX IF NOT EXISTS ix_dim_customer_lookup
    ON analytics.dim_customer (customer_id, customer_segment, customer_region);

CREATE TABLE IF NOT EXISTS analytics.dim_product (
    sk_product BIGSERIAL PRIMARY KEY,
    product_id VARCHAR(20) NOT NULL UNIQUE,
    product_name VARCHAR(200) NOT NULL,
    product_category VARCHAR(100) NOT NULL,
    product_subcategory VARCHAR(100) NOT NULL,
    unit_cost NUMERIC(12, 2) NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_dim_product_category
    ON analytics.dim_product (product_category, product_subcategory);

CREATE TABLE IF NOT EXISTS analytics.dim_time (
    time_key INTEGER PRIMARY KEY,
    calendar_date DATE NOT NULL UNIQUE,
    year_number INTEGER NOT NULL,
    quarter_number INTEGER NOT NULL,
    month_number INTEGER NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    day_number INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_dim_time_reporting
    ON analytics.dim_time (year_number, month_number, calendar_date);

CREATE TABLE IF NOT EXISTS analytics.dim_store_channel (
    sk_store_channel BIGSERIAL PRIMARY KEY,
    store_id VARCHAR(20) NOT NULL UNIQUE,
    store_name VARCHAR(200) NOT NULL,
    store_channel VARCHAR(30) NOT NULL,
    store_region VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_dim_store_channel_region
    ON analytics.dim_store_channel (store_channel, store_region);