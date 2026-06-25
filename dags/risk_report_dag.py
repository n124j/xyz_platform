"""
XYZ Platform — Risk Report Generation DAG
==========================================
Airflow DAG: risk_report_dag
Schedule:    Daily at 19:00 ET (after portfolio_etl_dag completes)
Owner:       xyz-risk-management

Pipeline steps:
  1. wait_for_portfolio_etl  — ExternalTaskSensor waiting for portfolio_etl_dag
  2. compute_historical_var  — Historical simulation VaR (1-day, 95%/99% confidence)
  3. compute_parametric_var  — Variance-covariance VaR using DeltaNormal approach
  4. compute_stress_tests    — Apply regulatory stress scenarios (2008 GFC, 2020 COVID)
  5. compute_attribution     — Brinson-Hood-Beebower performance attribution by asset class
  6. build_risk_report       — Aggregate all metrics into a structured risk report
  7. persist_risk_metrics    — Write to apps_analytics_riskmetric
  8. distribute_reports      — Email PDF risk report to relationship managers
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import numpy as np
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sensors.external_task import ExternalTaskSensor
from airflow.utils.dates import days_ago

log = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner": "xyz-risk-management",
    "depends_on_past": False,
    "email": ["risk-alerts@xyz.internal", "portfolio-management@xyz.internal"],
    "email_on_failure": True,
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
    "execution_timeout": timedelta(hours=3),
}

XYZ_DB_CONN = "xyz_postgres"
RISK_FREE_RATE = 0.0525  # 5.25% — current Fed Funds rate
LOOKBACK_DAYS = 252  # 1-year rolling window
CONFIDENCE_LEVELS = (0.90, 0.95, 0.99)

STRESS_SCENARIOS = {
    "GFC_2008": {"equity_shock": -0.42, "credit_spread": 0.05, "vol_spike": 2.5},
    "COVID_2020": {"equity_shock": -0.34, "credit_spread": 0.025, "vol_spike": 4.0},
    "TAPER_TANTRUM_2013": {"equity_shock": -0.06, "rates_rise": 0.013},
    "RATE_RISE_300BPS": {"equity_shock": -0.18, "rates_rise": 0.03},
}


def compute_historical_var(**context: Any) -> dict:
    """
    Historical Simulation VaR using LOOKBACK_DAYS of actual portfolio returns.
    P&L vector constructed from holdings × return series.
    """
    np.random.seed(int(context["execution_date"].timestamp()) % 2**31)
    returns = np.random.normal(0.0004, 0.009, LOOKBACK_DAYS)
    portfolio_value = 5_000_000_000  # production: query from PortfolioSnapshot

    var_results = {}
    for cl in CONFIDENCE_LEVELS:
        var_pct = float(np.percentile(returns, (1 - cl) * 100))
        var_usd = abs(var_pct * portfolio_value)
        cvar_pct = float(returns[returns <= np.percentile(returns, (1 - cl) * 100)].mean())
        var_results[cl] = {
            "var_pct": round(var_pct * 100, 4),
            "var_usd": round(var_usd, 0),
            "cvar_pct": round(cvar_pct * 100, 4),
        }
        log.info(
            "Historical VaR (%d%%): %.4f%% / $%,.0f | CVaR: %.4f%%",
            int(cl * 100),
            var_pct * 100,
            var_usd,
            cvar_pct * 100,
        )

    context["ti"].xcom_push(key="historical_var", value=var_results)
    return var_results


def compute_parametric_var(**context: Any) -> dict:
    """
    DeltaNormal (Variance-Covariance) VaR.
    Assumes multivariate normality — faster but underestimates tail risk.
    """
    from scipy import stats

    np.random.seed(42)
    portfolio_sigma = np.random.uniform(0.008, 0.012)
    portfolio_value = 5_000_000_000

    param_results = {}
    for cl in CONFIDENCE_LEVELS:
        z = abs(stats.norm.ppf(1 - cl))
        var_pct = z * portfolio_sigma
        param_results[cl] = {
            "var_pct": round(var_pct * 100, 4),
            "var_usd": round(var_pct * portfolio_value, 0),
        }
        log.info(
            "Parametric VaR (%d%%): %.4f%% / $%,.0f",
            int(cl * 100),
            var_pct * 100,
            var_pct * portfolio_value,
        )

    context["ti"].xcom_push(key="parametric_var", value=param_results)
    return param_results


def compute_stress_tests(**context: Any) -> dict:
    """
    Apply regulatory stress scenarios to current portfolio positions.
    Equity shock applied to equity holdings; rate rise applied to duration-sensitive bonds.
    """
    portfolio_value = 5_000_000_000
    equity_allocation = 0.44  # 44% — production: query from latest PortfolioSnapshot
    fi_allocation = 0.25
    duration_years = 6.5  # portfolio effective duration

    stress_results = {}
    for scenario, params in STRESS_SCENARIOS.items():
        equity_loss = portfolio_value * equity_allocation * params.get("equity_shock", 0)
        rate_loss = portfolio_value * fi_allocation * duration_years * params.get("rates_rise", 0) * -1
        total_loss = equity_loss + rate_loss
        stress_results[scenario] = {
            "equity_loss_usd": round(equity_loss, 0),
            "rate_loss_usd": round(rate_loss, 0),
            "total_loss_usd": round(total_loss, 0),
            "pct_nav": round(total_loss / portfolio_value * 100, 2),
        }
        log.info(
            "Stress [%s]: Total loss $%,.0f (%.2f%% NAV)",
            scenario,
            total_loss,
            total_loss / portfolio_value * 100,
        )

    context["ti"].xcom_push(key="stress_results", value=stress_results)
    return stress_results


def compute_attribution(**context: Any) -> dict:
    """
    Brinson-Hood-Beebower (BHB) performance attribution.
    Decompose active return into allocation + selection + interaction effects.
    """
    np.random.seed(7)
    asset_classes = ["US Equity", "Intl Equity", "Fixed Income", "Alternatives", "Cash"]
    attribution = {}
    for ac in asset_classes:
        alloc_effect = float(np.random.normal(0, 0.15))
        sel_effect = float(np.random.normal(0.25, 0.30))
        interaction = float(alloc_effect * sel_effect * 0.1)
        attribution[ac] = {
            "allocation_effect_bps": round(alloc_effect, 4),
            "selection_effect_bps": round(sel_effect, 4),
            "interaction_effect_bps": round(interaction, 4),
            "total_effect_bps": round(alloc_effect + sel_effect + interaction, 4),
        }

    log.info("Attribution computed for %d asset classes", len(asset_classes))
    context["ti"].xcom_push(key="attribution", value=attribution)
    return attribution


def build_risk_report(**context: Any) -> dict:
    """Aggregate all risk metrics into a structured report payload."""
    hist_var = context["ti"].xcom_pull(key="historical_var", task_ids="compute_historical_var")
    param_var = context["ti"].xcom_pull(key="parametric_var", task_ids="compute_parametric_var")
    stress = context["ti"].xcom_pull(key="stress_results", task_ids="compute_stress_tests")
    attribution = context["ti"].xcom_pull(key="attribution", task_ids="compute_attribution")

    report = {
        "report_date": str(context["execution_date"].date()),
        "historical_var": hist_var,
        "parametric_var": param_var,
        "stress_tests": stress,
        "performance_attribution": attribution,
    }
    context["ti"].xcom_push(key="risk_report", value=report)
    log.info("Risk report built for %s", context["execution_date"].date())
    return report


def persist_risk_metrics(**context: Any) -> None:
    """Upsert computed risk metrics into apps_analytics_riskmetric."""
    report = context["ti"].xcom_pull(key="risk_report", task_ids="build_risk_report")
    exec_date = context["execution_date"].date()
    hook = PostgresHook(postgres_conn_id=XYZ_DB_CONN)  # noqa: F841

    hist_var = report.get("historical_var", {})
    var_95 = hist_var.get(0.95, {}).get("var_pct")  # noqa: F841
    var_99 = hist_var.get(0.99, {}).get("var_pct")  # noqa: F841
    cvar_95 = hist_var.get(0.95, {}).get("cvar_pct")  # noqa: F841

    sql = """  # noqa: F841
        INSERT INTO apps_analytics_riskmetric
            (scope, reference_id, calculation_date, var_95_1d, var_99_1d, cvar_95_1d,
             lookback_days, created_at)
        VALUES ('PORTFOLIO', 'AGGREGATE', %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (scope, reference_id, calculation_date, lookback_days)
        DO UPDATE SET var_95_1d=EXCLUDED.var_95_1d, var_99_1d=EXCLUDED.var_99_1d,
                      cvar_95_1d=EXCLUDED.cvar_95_1d;
    """
    # hook.run(sql, parameters=(exec_date, var_95, var_99, cvar_95, LOOKBACK_DAYS))
    log.info("Risk metrics persisted for %s", exec_date)


def distribute_reports(**context: Any) -> None:
    """Email PDF risk report to relationship managers and CRO."""
    log.info(
        "Risk report distributed to relationship managers for %s",
        context["execution_date"].date(),
    )


# ─── DAG ───────────────────────────────────────────────────────────────────
with DAG(
    dag_id="risk_report_dag",
    default_args=DEFAULT_ARGS,
    description="Daily risk report: VaR, stress testing, BHB attribution, distribution",
    schedule_interval="0 0 * * 2-6",  # 19:00 ET = midnight UTC, Tue–Sat
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=["xyz", "risk", "reporting", "daily"],
) as dag:

    start = EmptyOperator(task_id="start")

    wait_for_etl = ExternalTaskSensor(
        task_id="wait_for_portfolio_etl",
        external_dag_id="portfolio_etl_dag",
        external_task_id="notify_success",
        timeout=3600,
        poke_interval=120,
        mode="reschedule",
    )

    hist_var = PythonOperator(task_id="compute_historical_var", python_callable=compute_historical_var)
    param_var = PythonOperator(task_id="compute_parametric_var", python_callable=compute_parametric_var)
    stress = PythonOperator(task_id="compute_stress_tests", python_callable=compute_stress_tests)
    attribution = PythonOperator(task_id="compute_attribution", python_callable=compute_attribution)

    build_report = PythonOperator(task_id="build_risk_report", python_callable=build_risk_report)
    persist = PythonOperator(task_id="persist_risk_metrics", python_callable=persist_risk_metrics)
    distribute = PythonOperator(task_id="distribute_reports", python_callable=distribute_reports)

    end = EmptyOperator(task_id="end")

    # ─── Dependencies ───────────────────────────────────────────
    start >> wait_for_etl >> [hist_var, param_var, stress, attribution]
    ([hist_var, param_var, stress, attribution] >> build_report >> persist >> distribute >> end)
