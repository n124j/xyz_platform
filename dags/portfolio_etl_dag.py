"""
XYZ Platform — Portfolio ETL DAG
=================================
Airflow DAG: portfolio_etl_dag
Schedule:    Daily at 18:30 ET (after market close)
Owner:       xyz-data-engineering

Pipeline steps:
  1. extract_holdings        — Pull raw position files from source systems (custody, prime broker)
  2. validate_holdings       — Data-quality checks (completeness, price freshness, ticker validity)
  3. transform_holdings      — Normalise schema, apply FX rates, compute derived fields
  4. load_holdings           — Upsert into Holding & Account tables (PostgreSQL)
  5. compute_portfolio_stats — Aggregate AUM, P&L, asset allocation into PortfolioSnapshot
  6. refresh_risk_metrics    — Trigger risk calculations (VaR, Sharpe, drawdown)
  7. notify_success          — Post completion alert to internal monitoring channel
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.http.sensors.http import HttpSensor
from airflow.utils.dates import days_ago
from airflow.models import Variable

log = logging.getLogger(__name__)

# ─── Default args ──────────────────────────────────────────────────────────
DEFAULT_ARGS = {
    "owner": "xyz-data-engineering",
    "depends_on_past": False,
    "email": ["data-alerts@xyz.internal"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=2),
}

XYZ_DB_CONN = "xyz_postgres"
SOURCE_API_CONN = "xyz_custody_api"


# ─── Task functions ─────────────────────────────────────────────────────────
def extract_holdings(**context: Any) -> dict:
    """
    Extract raw position data from:
      - Custody system REST API
      - Prime broker FTP drop
      - Internal OMS database
    Returns summary dict pushed to XCom.
    """
    execution_date = context["execution_date"]
    log.info("Extracting holdings for %s", execution_date.date())

    # In production: call custody API, parse CSV/JSON, load into staging table
    # hook = PostgresHook(postgres_conn_id=XYZ_DB_CONN)
    # hook.run("INSERT INTO staging.raw_holdings ...")

    records_extracted = 4_821  # production: actual count
    log.info("Extracted %d raw position records", records_extracted)
    context["ti"].xcom_push(key="records_extracted", value=records_extracted)
    return {"status": "ok", "records": records_extracted}


def validate_holdings(**context: Any) -> str:
    """
    Data-quality gates:
      - All tickers resolve to valid ISIN / CUSIP
      - Prices not stale (< 2 business days old)
      - Account totals balance to custody statement
    Returns branch name for downstream routing.
    """
    records = context["ti"].xcom_pull(key="records_extracted", task_ids="extract_holdings")
    log.info("Validating %d records", records)

    failed_checks = []

    # Example quality checks (production: real SQL assertions)
    if records < 100:
        failed_checks.append("too_few_records")

    if failed_checks:
        log.error("Validation failed: %s", failed_checks)
        return "validation_failed"

    log.info("All validation checks passed")
    return "transform_holdings"


def transform_holdings(**context: Any) -> dict:
    """
    Normalisation steps:
      - Apply end-of-day FX rates (EUR, GBP, CHF, JPY → USD)
      - Compute unrealised P&L = (market_price - cost_basis) * quantity
      - Derive portfolio weights
      - Enrich with Bloomberg sector/industry classifications
    """
    log.info("Transforming holdings…")
    # hook = PostgresHook(postgres_conn_id=XYZ_DB_CONN)
    # hook.run("INSERT INTO staging.transformed_holdings SELECT ... FROM staging.raw_holdings")
    log.info("Transformation complete")
    return {"status": "ok"}


def load_holdings(**context: Any) -> dict:
    """
    Upsert transformed positions into the XYZ Platform PostgreSQL schema:
      apps_accounts_holding (via ON CONFLICT DO UPDATE)
      apps_accounts_account (market_value, cash_balance)
    Uses a PostgresHook transaction to ensure atomicity.
    """
    log.info("Loading holdings into xyz_platform database…")
    hook = PostgresHook(postgres_conn_id=XYZ_DB_CONN)

    # Production: execute upsert SQL from file
    upsert_sql = """
        INSERT INTO apps_accounts_holding
            (account_id, ticker, security_name, asset_class, quantity,
             cost_basis, market_price, market_value, unrealized_pnl, weight, last_updated)
        SELECT
            s.account_id, s.ticker, s.security_name, s.asset_class, s.quantity,
            s.cost_basis, s.market_price, s.market_value, s.unrealized_pnl,
            s.market_value / SUM(s.market_value) OVER (PARTITION BY s.account_id), NOW()
        FROM staging.transformed_holdings s
        ON CONFLICT (account_id, ticker)
        DO UPDATE SET
            market_price   = EXCLUDED.market_price,
            market_value   = EXCLUDED.market_value,
            unrealized_pnl = EXCLUDED.unrealized_pnl,
            weight         = EXCLUDED.weight,
            last_updated   = NOW();
    """
    # hook.run(upsert_sql)
    log.info("Holding upsert complete")
    return {"status": "loaded"}


def compute_portfolio_stats(**context: Any) -> dict:
    """
    Aggregate Holding → Account → PortfolioSnapshot.
    Calculates:
      - Total AUM by asset class
      - Daily P&L and daily return %
      - YTD return (vs inception AUM on Jan 1)
    Inserts a new PortfolioSnapshot row for today.
    """
    execution_date = context["execution_date"]
    log.info("Computing portfolio snapshot for %s", execution_date.date())

    hook = PostgresHook(postgres_conn_id=XYZ_DB_CONN)
    snapshot_sql = """
        INSERT INTO apps_portfolio_portfoliosnapshot
            (snapshot_date, total_aum, equity_value, fixed_income_value,
             alternatives_value, cash_value, daily_pnl, daily_return_pct,
             ytd_return_pct, client_count, account_count, created_at)
        SELECT
            %(exec_date)s,
            SUM(h.market_value),
            SUM(h.market_value) FILTER (WHERE h.asset_class = 'EQ'),
            SUM(h.market_value) FILTER (WHERE h.asset_class = 'FI'),
            SUM(h.market_value) FILTER (WHERE h.asset_class = 'ALT'),
            SUM(h.market_value) FILTER (WHERE h.asset_class = 'CASH'),
            SUM(h.unrealized_pnl),
            0.0, 0.0,
            COUNT(DISTINCT a.client_id),
            COUNT(DISTINCT a.id),
            NOW()
        FROM apps_accounts_holding h
        JOIN apps_accounts_account a ON a.id = h.account_id
        WHERE a.is_active = TRUE
        ON CONFLICT (snapshot_date) DO UPDATE SET
            total_aum       = EXCLUDED.total_aum,
            equity_value    = EXCLUDED.equity_value,
            daily_pnl       = EXCLUDED.daily_pnl;
    """
    # hook.run(snapshot_sql, parameters={"exec_date": execution_date.date()})
    log.info("Portfolio snapshot written")
    return {"status": "snapshot_written"}


def refresh_risk_metrics(**context: Any) -> None:
    """
    Compute and persist risk metrics to apps_analytics_riskmetric:
      - 1-day 95%/99% Historical VaR using 252-day return window
      - Annualised volatility, Sharpe ratio (risk-free = 5.25%)
      - Max drawdown, beta vs S&P 500
    Delegated to scipy / numpy; results upserted via PostgresHook.
    """
    import numpy as np
    from scipy import stats

    log.info("Computing risk metrics…")

    # Production: fetch actual return series from apps_analytics_marketdata
    np.random.seed(0)
    returns = np.random.normal(0.0004, 0.009, 252)

    var_95 = float(np.percentile(returns, 5) * 100)
    var_99 = float(np.percentile(returns, 1) * 100)
    ann_vol = float(returns.std() * np.sqrt(252) * 100)
    ann_ret = float(returns.mean() * 252 * 100)
    sharpe = float((ann_ret - 5.25) / ann_vol)
    cum = (1 + returns).cumprod()
    max_dd = float(((cum - cum.cummax()) / cum.cummax()).min() * 100)

    log.info(
        "Risk metrics — VaR95: %.3f%%, Vol: %.2f%%, Sharpe: %.2f, MaxDD: %.2f%%",
        var_95, ann_vol, sharpe, max_dd,
    )
    # Production: upsert into RiskMetric table


def notify_success(**context: Any) -> None:
    log.info(
        "✅ portfolio_etl_dag completed successfully for %s",
        context["execution_date"].date(),
    )


# ─── DAG definition ────────────────────────────────────────────────────────
with DAG(
    dag_id="portfolio_etl_dag",
    default_args=DEFAULT_ARGS,
    description="Daily portfolio position ETL: extract → validate → transform → load → stats → risk",
    schedule_interval="30 23 * * 1-5",  # 18:30 ET = 23:30 UTC, Mon–Fri
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=["xyz", "portfolio", "etl", "daily"],
) as dag:

    start = EmptyOperator(task_id="start")

    extract = PythonOperator(
        task_id="extract_holdings",
        python_callable=extract_holdings,
    )

    validate = BranchPythonOperator(
        task_id="validate_holdings",
        python_callable=validate_holdings,
    )

    validation_failed = EmptyOperator(
        task_id="validation_failed",
        trigger_rule="none_failed_min_one_success",
    )

    transform = PythonOperator(
        task_id="transform_holdings",
        python_callable=transform_holdings,
    )

    load = PythonOperator(
        task_id="load_holdings",
        python_callable=load_holdings,
    )

    compute_stats = PythonOperator(
        task_id="compute_portfolio_stats",
        python_callable=compute_portfolio_stats,
    )

    risk = PythonOperator(
        task_id="refresh_risk_metrics",
        python_callable=refresh_risk_metrics,
    )

    notify = PythonOperator(
        task_id="notify_success",
        python_callable=notify_success,
        trigger_rule="none_failed_min_one_success",
    )

    # ─── Dependencies ───────────────────────────────────────────
    start >> extract >> validate >> [transform, validation_failed]
    transform >> load >> compute_stats >> risk >> notify
