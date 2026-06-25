#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE ${POSTGRES_DB}_airflow;
    GRANT ALL PRIVILEGES ON DATABASE ${POSTGRES_DB}_airflow TO ${POSTGRES_USER};
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE SCHEMA IF NOT EXISTS staging;
    GRANT ALL ON SCHEMA staging TO ${POSTGRES_USER};

    CREATE TABLE IF NOT EXISTS staging.raw_holdings (
        id              BIGSERIAL PRIMARY KEY,
        account_number  VARCHAR(20),
        ticker          VARCHAR(20),
        security_name   VARCHAR(255),
        asset_class     VARCHAR(10),
        quantity        NUMERIC(18,6),
        cost_basis      NUMERIC(20,4),
        market_price    NUMERIC(20,4),
        market_value    NUMERIC(20,2),
        source_file     VARCHAR(255),
        loaded_at       TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS staging.transformed_holdings (
        LIKE staging.raw_holdings INCLUDING ALL,
        unrealized_pnl  NUMERIC(20,2),
        fx_rate         NUMERIC(10,6) DEFAULT 1.0,
        validated_at    TIMESTAMPTZ
    );
EOSQL
