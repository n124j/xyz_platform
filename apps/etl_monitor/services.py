"""
XYZ Platform — Airflow REST API Service

Polls the Airflow v1 API and syncs DAG run data into the
local ETL monitor database tables via Celery periodic tasks.
"""
import logging
import requests
from django.conf import settings
from django.utils import timezone
from .models import DAGRun, TaskInstance, PipelineAlert

logger = logging.getLogger(__name__)

AIRFLOW_SESSION = requests.Session()
AIRFLOW_SESSION.auth = (settings.AIRFLOW_API_USER, settings.AIRFLOW_API_PASSWORD)
AIRFLOW_SESSION.headers.update({"Content-Type": "application/json"})


def _airflow_get(path: str, **params) -> dict:
    url = f"{settings.AIRFLOW_API_URL}{path}"
    resp = AIRFLOW_SESSION.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def list_dags() -> list:
    """Return all active DAGs registered in Airflow."""
    data = _airflow_get("/dags", only_active=True)
    return data.get("dags", [])


def sync_dag_runs(dag_id: str, limit: int = 10) -> int:
    """
    Pull the latest <limit> runs for dag_id from Airflow,
    upsert them into DAGRun, and raise PipelineAlert on failure.
    Returns number of records synced.
    """
    data = _airflow_get(f"/dags/{dag_id}/dagRuns", limit=limit, order_by="-execution_date")
    runs = data.get("dag_runs", [])
    synced = 0

    for run in runs:
        duration = None
        if run.get("start_date") and run.get("end_date"):
            from datetime import datetime
            start = datetime.fromisoformat(run["start_date"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(run["end_date"].replace("Z", "+00:00"))
            duration = (end - start).total_seconds()

        dag_run, created = DAGRun.objects.update_or_create(
            dag_run_id=run["dag_run_id"],
            defaults={
                "dag_id": dag_id,
                "run_type": run.get("run_type", "scheduled"),
                "state": run["state"],
                "execution_date": run["execution_date"],
                "start_date": run.get("start_date"),
                "end_date": run.get("end_date"),
                "duration_seconds": duration,
                "conf": run.get("conf", {}),
            },
        )

        if run["state"] == "failed":
            PipelineAlert.objects.get_or_create(
                dag_run=dag_run,
                defaults={
                    "dag_id": dag_id,
                    "severity": PipelineAlert.Severity.CRITICAL,
                    "message": f"DAG run {run['dag_run_id']} failed at {run.get('end_date', 'unknown')}",
                },
            )
            logger.error("DAG %s run %s failed", dag_id, run["dag_run_id"])

        synced += 1

    return synced


def trigger_dag(dag_id: str, conf: dict = None) -> dict:
    """Trigger a new DAG run via Airflow REST API."""
    url = f"{settings.AIRFLOW_API_URL}/dags/{dag_id}/dagRuns"
    payload = {"conf": conf or {}}
    resp = AIRFLOW_SESSION.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()
