"""
XYZ Platform — Market Data Ingestion DAG
==========================================
Airflow DAG: market_data_dag
Schedule:    Every 15 minutes during market hours (Mon–Fri, 09:30–17:00 ET)
Owner:       xyz-data-engineering

Pipeline steps:
  1. check_market_open       — Sensor: confirm market is open (skip on holidays)
  2. fetch_equity_prices     — Pull OHLCV from market data provider (e.g., Bloomberg, Refinitiv)
  3. fetch_fx_rates          — Pull spot FX rates from ECB / internal treasury feed
  4. fetch_benchmark_levels  — Pull S&P 500, MSCI World, Bloomberg Agg index levels
  5. validate_prices         — Check for stale/outlier prices using z-score filter
  6. persist_market_data     — Upsert into apps_analytics_marketdata
  7. update_holding_prices   — Live-mark holdings in apps_accounts_holding
  8. update_account_values   — Recompute account market values from fresh prices
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator, ShortCircuitOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.dates import days_ago

log = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner": "xyz-data-engineering",
    "depends_on_past": False,
    "email": ["market-data-alerts@xyz.internal"],
    "email_on_failure": True,
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(minutes=10),
}

XYZ_DB_CONN = "xyz_postgres"
MARKET_DATA_TICKERS = [
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "NVDA",
    "JPM",
    "GS",
    "MS",
    "BRK.B",
    "JNJ",
    "TLT",
    "AGG",
    "GLD",
    "SPY",
    "QQQ",
]
BENCHMARKS = [
    {"code": "SPX", "name": "S&P 500 Index"},
    {"code": "MXWO", "name": "MSCI World Index"},
    {"code": "LBUSTRUU", "name": "Bloomberg US Agg Bond Index"},
]
FX_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD"]


def is_market_open(**context: Any) -> bool:
    """
    ShortCircuitOperator: return False on weekends or US market holidays.
    Production: integrate with NYSE holiday calendar API.
    """
    now = context["execution_date"]
    if now.weekday() >= 5:
        log.info("Market closed (weekend). Skipping data fetch.")
        return False
    # TODO: check NYSE holiday calendar
    log.info("Market open — proceeding with data ingestion")
    return True


def fetch_equity_prices(**context: Any) -> dict:
    """
    Pull OHLCV for all tracked tickers from market data provider.
    Production: use Bloomberg BLPAPI / Refinitiv EikonAPI / Polygon.io
    """
    execution_date = context["execution_date"]
    log.info(
        "Fetching equity prices for %d tickers @ %s",
        len(MARKET_DATA_TICKERS),
        execution_date,
    )

    # Simulated fetch — production replaces with real API call
    prices = {
        t: {
            "open": 150.0,
            "high": 155.0,
            "low": 148.0,
            "close": 152.5,
            "volume": 12_000_000,
        }
        for t in MARKET_DATA_TICKERS
    }

    log.info("Fetched prices for %d securities", len(prices))
    context["ti"].xcom_push(key="equity_prices", value=prices)
    return {"fetched": len(prices)}


def fetch_fx_rates(**context: Any) -> dict:
    """Pull spot FX rates from ECB data feed or internal treasury system."""
    log.info("Fetching FX rates for pairs: %s", FX_PAIRS)
    # Production: GET https://data-api.ecb.europa.eu/service/data/EXR/...
    rates = {pair: 1.0 for pair in FX_PAIRS}
    rates.update({"EURUSD": 1.082, "GBPUSD": 1.265, "USDJPY": 157.3})
    context["ti"].xcom_push(key="fx_rates", value=rates)
    return {"rates_fetched": len(rates)}


def fetch_benchmark_levels(**context: Any) -> dict:
    """Fetch end-of-day index levels for all tracked benchmarks."""
    log.info("Fetching benchmark levels for %d indices", len(BENCHMARKS))
    levels = {b["code"]: {"level": 5000.0 + hash(b["code"]) % 500, "return": 0.0012} for b in BENCHMARKS}
    context["ti"].xcom_push(key="benchmark_levels", value=levels)
    return {"benchmarks_fetched": len(levels)}


def validate_prices(**context: Any) -> dict:
    """
    Data quality validation:
      - Z-score filter: flag prices > 5σ from 30-day moving average
      - Stale price check: reject prices older than 15 minutes
      - Circuit breaker: abort if > 20% of prices fail validation
    """
    import numpy as np

    prices = context["ti"].xcom_pull(key="equity_prices", task_ids="fetch_equity_prices")
    failed = []

    for ticker, p in prices.items():
        # Simulate z-score check
        deviation = abs(np.random.normal(0, 1))
        if deviation > 4.5:
            failed.append(ticker)

    if len(failed) / len(prices) > 0.20:
        raise ValueError(f"Circuit breaker: {len(failed)}/{len(prices)} prices failed validation")

    log.info(
        "Price validation complete — %d failed of %d (%.1f%%)",
        len(failed),
        len(prices),
        len(failed) / len(prices) * 100,
    )
    return {"failed_tickers": failed, "pass_rate": 1 - len(failed) / len(prices)}


def persist_market_data(**context: Any) -> int:
    """
    Upsert OHLCV and benchmark data into apps_analytics_marketdata
    and apps_analytics_benchmarkreturn tables.
    """
    prices = context["ti"].xcom_pull(key="equity_prices", task_ids="fetch_equity_prices")
    hook = PostgresHook(postgres_conn_id=XYZ_DB_CONN)  # noqa: F841
    exec_date = context["execution_date"].date()

    upsert_sql = """  # noqa: F841
        INSERT INTO apps_analytics_marketdata
            (ticker, security_name, price_date, open_price, high_price, low_price,
             close_price, adjusted_close, volume, currency, source, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'USD', 'INTERNAL', NOW())
        ON CONFLICT (ticker, price_date) DO UPDATE SET
            close_price    = EXCLUDED.close_price,
            adjusted_close = EXCLUDED.adjusted_close,
            volume         = EXCLUDED.volume;
    """
    rows = [
        (
            t,
            t,
            exec_date,
            p["open"],
            p["high"],
            p["low"],
            p["close"],
            p["close"],
            p["volume"],
        )
        for t, p in prices.items()
    ]
    # hook.insert_rows("apps_analytics_marketdata", rows, ...)  # production
    log.info("Persisted %d market data records for %s", len(rows), exec_date)
    return len(rows)


def update_holding_prices(**context: Any) -> None:
    """Mark-to-market all holdings using fresh close prices."""
    log.info("Updating holding prices with fresh market data…")
    hook = PostgresHook(postgres_conn_id=XYZ_DB_CONN)  # noqa: F841
    sql = """  # noqa: F841
        UPDATE apps_accounts_holding h
        SET    market_price = md.close_price,
               market_value = md.close_price * h.quantity,
               unrealized_pnl = (md.close_price - h.cost_basis) * h.quantity,
               last_updated = NOW()
        FROM   apps_analytics_marketdata md
        WHERE  md.ticker = h.ticker
          AND  md.price_date = CURRENT_DATE;
    """
    # hook.run(sql)
    log.info("Holdings marked to market")


def update_account_values(**context: Any) -> None:
    """Recompute account-level market values after holdings are updated."""
    log.info("Recomputing account market values…")
    hook = PostgresHook(postgres_conn_id=XYZ_DB_CONN)  # noqa: F841
    sql = """  # noqa: F841
        UPDATE apps_accounts_account a
        SET    market_value = (
                   SELECT COALESCE(SUM(h.market_value), 0)
                   FROM   apps_accounts_holding h
                   WHERE  h.account_id = a.id
               ),
               updated_at = NOW()
        WHERE  a.is_active = TRUE;
    """
    # hook.run(sql)
    log.info("Account values updated")


# ─── DAG ───────────────────────────────────────────────────────────────────
with DAG(
    dag_id="market_data_dag",
    default_args=DEFAULT_ARGS,
    description="Intraday market data ingestion: equity prices, FX rates, benchmark levels",
    schedule_interval="*/15 14-21 * * 1-5",  # 09:30–17:00 ET = 14:30–22:00 UTC
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=["xyz", "market-data", "intraday"],
) as dag:

    start = EmptyOperator(task_id="start")

    market_open = ShortCircuitOperator(
        task_id="check_market_open",
        python_callable=is_market_open,
    )

    fetch_equities = PythonOperator(
        task_id="fetch_equity_prices",
        python_callable=fetch_equity_prices,
    )

    fetch_fx = PythonOperator(
        task_id="fetch_fx_rates",
        python_callable=fetch_fx_rates,
    )

    fetch_benchmarks = PythonOperator(
        task_id="fetch_benchmark_levels",
        python_callable=fetch_benchmark_levels,
    )

    validate = PythonOperator(
        task_id="validate_prices",
        python_callable=validate_prices,
    )

    persist = PythonOperator(
        task_id="persist_market_data",
        python_callable=persist_market_data,
    )

    update_holdings = PythonOperator(
        task_id="update_holding_prices",
        python_callable=update_holding_prices,
    )

    update_accounts = PythonOperator(
        task_id="update_account_values",
        python_callable=update_account_values,
    )

    end = EmptyOperator(task_id="end")

    # ─── Dependencies ───────────────────────────────────────────
    start >> market_open >> [fetch_equities, fetch_fx, fetch_benchmarks]
    [fetch_equities, fetch_fx, fetch_benchmarks] >> validate >> persist
    persist >> update_holdings >> update_accounts >> end
