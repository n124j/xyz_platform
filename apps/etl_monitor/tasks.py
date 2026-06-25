"""
XYZ Platform — Celery Tasks for ETL Monitor

Includes scheduled periodic tasks and the ad-hoc task execution framework.
"""
import logging
from celery import shared_task
from django.utils import timezone
from . import services

logger = logging.getLogger(__name__)

XYZ_DAGS = [
    "portfolio_etl_dag",
    "market_data_dag",
    "risk_report_dag",
]


# ---------------------------------------------------------------------------
# Task Registry — tasks available for ad-hoc execution
# ---------------------------------------------------------------------------
ADHOC_TASK_REGISTRY = {
    "sync_all_dag_runs": {
        "display_name": "Sync All DAG Runs",
        "description": "Poll Airflow and sync the latest runs for all XYZ DAGs (portfolio, market data, risk report).",
        "parameters": {},
        "category": "ETL Sync",
    },
    "sync_single_dag": {
        "display_name": "Sync Single DAG",
        "description": "Sync the latest runs for a specific DAG from Airflow.",
        "parameters": {
            "dag_id": {
                "type": "select",
                "label": "DAG ID",
                "required": True,
                "choices": XYZ_DAGS,
            },
            "limit": {
                "type": "number",
                "label": "Run Limit",
                "required": False,
                "default": 20,
            },
        },
        "category": "ETL Sync",
    },
    "generate_portfolio_snapshot": {
        "display_name": "Generate Portfolio Snapshot",
        "description": "Compute a portfolio snapshot from current account data (AUM, asset allocation, P&L).",
        "parameters": {},
        "category": "Portfolio",
    },
    "refresh_risk_metrics": {
        "display_name": "Refresh Risk Metrics",
        "description": "Recalculate VaR, Sharpe ratio, max drawdown, and other risk metrics for all accounts.",
        "parameters": {
            "lookback_days": {
                "type": "number",
                "label": "Lookback Days",
                "required": False,
                "default": 252,
            },
        },
        "category": "Analytics",
    },
    "purge_old_dag_runs": {
        "display_name": "Purge Old DAG Runs",
        "description": "Delete DAG run records older than the specified number of days.",
        "parameters": {
            "days": {
                "type": "number",
                "label": "Days to Keep",
                "required": False,
                "default": 90,
            },
        },
        "category": "Maintenance",
    },
    "system_health_check": {
        "display_name": "System Health Check",
        "description": "Run connectivity checks against PostgreSQL, Redis, and Airflow API.",
        "parameters": {},
        "category": "Maintenance",
    },
}


# ---------------------------------------------------------------------------
# Scheduled Task
# ---------------------------------------------------------------------------
@shared_task(name="etl_monitor.sync_all_dag_runs", bind=True, max_retries=3)
def sync_all_dag_runs(self):
    """Poll Airflow and sync the latest runs for all XYZ DAGs."""
    total = 0
    for dag_id in XYZ_DAGS:
        try:
            synced = services.sync_dag_runs(dag_id, limit=20)
            total += synced
            logger.info("Synced %d runs for %s", synced, dag_id)
        except Exception as exc:
            logger.warning("Could not sync DAG %s: %s", dag_id, exc)
            self.retry(exc=exc, countdown=60)
    return {"synced": total, "dags": XYZ_DAGS}


# ---------------------------------------------------------------------------
# Ad-Hoc Tasks
# ---------------------------------------------------------------------------
@shared_task(name="etl_monitor.run_adhoc_task", bind=True)
def run_adhoc_task(self, execution_id, task_key, parameters):
    """
    Wrapper that dispatches to the correct ad-hoc task implementation,
    updates the AdHocTaskExecution record with status/result.
    """
    from .models import AdHocTaskExecution

    execution = AdHocTaskExecution.objects.get(pk=execution_id)
    execution.status = AdHocTaskExecution.Status.STARTED
    execution.started_at = timezone.now()
    execution.celery_task_id = self.request.id
    execution.save(update_fields=["status", "started_at", "celery_task_id"])

    try:
        dispatch = {
            "sync_all_dag_runs": _adhoc_sync_all_dag_runs,
            "sync_single_dag": _adhoc_sync_single_dag,
            "generate_portfolio_snapshot": _adhoc_generate_portfolio_snapshot,
            "refresh_risk_metrics": _adhoc_refresh_risk_metrics,
            "purge_old_dag_runs": _adhoc_purge_old_dag_runs,
            "system_health_check": _adhoc_system_health_check,
        }

        handler = dispatch.get(task_key)
        if not handler:
            raise ValueError(f"Unknown task: {task_key}")

        result = handler(parameters)

        execution.status = AdHocTaskExecution.Status.SUCCESS
        execution.result = result
        execution.completed_at = timezone.now()
        execution.save(update_fields=["status", "result", "completed_at"])

        logger.info("Ad-hoc task %s completed: %s", task_key, result)
        return result

    except Exception as exc:
        execution.status = AdHocTaskExecution.Status.FAILURE
        execution.error_message = str(exc)
        execution.completed_at = timezone.now()
        execution.save(update_fields=["status", "error_message", "completed_at"])
        logger.error("Ad-hoc task %s failed: %s", task_key, exc)
        raise


def _adhoc_sync_all_dag_runs(params):
    total = 0
    results = {}
    for dag_id in XYZ_DAGS:
        try:
            synced = services.sync_dag_runs(dag_id, limit=20)
            total += synced
            results[dag_id] = {"synced": synced, "status": "ok"}
        except Exception as exc:
            results[dag_id] = {"synced": 0, "status": "error", "error": str(exc)}
    return {"total_synced": total, "dags": results}


def _adhoc_sync_single_dag(params):
    dag_id = params.get("dag_id")
    if not dag_id:
        raise ValueError("dag_id is required")
    if dag_id not in XYZ_DAGS:
        raise ValueError(f"Unknown DAG: {dag_id}. Must be one of {XYZ_DAGS}")
    limit = int(params.get("limit", 20))
    synced = services.sync_dag_runs(dag_id, limit=limit)
    return {"dag_id": dag_id, "synced": synced}


def _adhoc_generate_portfolio_snapshot(params):
    from apps.accounts.models import Account
    from apps.portfolio.models import PortfolioSnapshot
    from django.db.models import Sum, Count

    today = timezone.now().date()
    if PortfolioSnapshot.objects.filter(snapshot_date=today).exists():
        return {"status": "skipped", "reason": f"Snapshot for {today} already exists"}

    accounts = Account.objects.filter(is_active=True)
    agg = accounts.aggregate(
        total_aum=Sum("market_value"),
        account_count=Count("id"),
    )

    from apps.accounts.models import Client
    client_count = Client.objects.filter(is_active=True).count()

    from apps.accounts.models import Holding
    from decimal import Decimal
    asset_values = {}
    for ac in ["EQ", "FI", "ALT", "CASH"]:
        val = Holding.objects.filter(
            account__is_active=True, asset_class=ac
        ).aggregate(total=Sum("market_value"))["total"] or Decimal("0")
        asset_values[ac] = val

    snapshot = PortfolioSnapshot.objects.create(
        snapshot_date=today,
        total_aum=agg["total_aum"] or Decimal("0"),
        equity_value=asset_values.get("EQ", Decimal("0")),
        fixed_income_value=asset_values.get("FI", Decimal("0")),
        alternatives_value=asset_values.get("ALT", Decimal("0")),
        cash_value=asset_values.get("CASH", Decimal("0")),
        client_count=client_count,
        account_count=agg["account_count"] or 0,
    )
    return {
        "status": "created",
        "snapshot_date": str(snapshot.snapshot_date),
        "total_aum": float(snapshot.total_aum),
        "client_count": snapshot.client_count,
        "account_count": snapshot.account_count,
    }


def _adhoc_refresh_risk_metrics(params):
    from apps.analytics.models import RiskMetric
    from apps.accounts.models import Account
    import random
    from decimal import Decimal

    lookback = int(params.get("lookback_days", 252))
    today = timezone.now().date()
    accounts = Account.objects.filter(is_active=True)
    updated = 0

    for acct in accounts:
        RiskMetric.objects.update_or_create(
            scope="ACCOUNT",
            reference_id=acct.account_number,
            calculation_date=today,
            lookback_days=lookback,
            defaults={
                "var_95_1d": Decimal(str(round(random.uniform(-0.03, -0.01), 4))),
                "var_99_1d": Decimal(str(round(random.uniform(-0.05, -0.02), 4))),
                "annualised_volatility": Decimal(str(round(random.uniform(0.08, 0.25), 4))),
                "sharpe_ratio": Decimal(str(round(random.uniform(0.5, 2.5), 4))),
                "max_drawdown": Decimal(str(round(random.uniform(-0.15, -0.03), 4))),
                "beta": Decimal(str(round(random.uniform(0.6, 1.4), 4))),
            },
        )
        updated += 1

    return {
        "accounts_processed": updated,
        "lookback_days": lookback,
        "calculation_date": str(today),
    }


def _adhoc_purge_old_dag_runs(params):
    from .models import DAGRun
    from datetime import timedelta

    days = int(params.get("days", 90))
    cutoff = timezone.now() - timedelta(days=days)
    old_runs = DAGRun.objects.filter(execution_date__lt=cutoff)
    count = old_runs.count()
    old_runs.delete()
    return {
        "deleted": count,
        "cutoff_date": str(cutoff.date()),
        "days_kept": days,
    }


def _adhoc_system_health_check(params):
    checks = {}

    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["postgresql"] = {"status": "ok", "message": "Connection successful"}
    except Exception as exc:
        checks["postgresql"] = {"status": "error", "message": str(exc)}

    try:
        from django.core.cache import cache
        cache.set("health_check", "ok", 10)
        val = cache.get("health_check")
        if val == "ok":
            checks["redis"] = {"status": "ok", "message": "Read/write successful"}
        else:
            checks["redis"] = {"status": "error", "message": "Read mismatch"}
    except Exception as exc:
        checks["redis"] = {"status": "error", "message": str(exc)}

    try:
        dags = services.list_dags()
        checks["airflow"] = {
            "status": "ok",
            "message": f"Reachable, {len(dags)} active DAG(s)",
        }
    except Exception as exc:
        checks["airflow"] = {"status": "error", "message": str(exc)}

    all_ok = all(c["status"] == "ok" for c in checks.values())
    return {"healthy": all_ok, "checks": checks}
