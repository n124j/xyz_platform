import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from apps.etl_monitor.services import sync_dag_runs, trigger_dag, list_dags
from apps.etl_monitor.models import DAGRun, PipelineAlert


@pytest.mark.django_db
class TestSyncDagRuns:
    @patch("apps.etl_monitor.services._airflow_get")
    def test_sync_successful_run(self, mock_get):
        mock_get.return_value = {
            "dag_runs": [
                {
                    "dag_run_id": "manual__2024-06-20",
                    "run_type": "manual",
                    "state": "success",
                    "execution_date": "2024-06-20T18:30:00+00:00",
                    "start_date": "2024-06-20T18:30:00+00:00",
                    "end_date": "2024-06-20T19:00:00+00:00",
                    "conf": {},
                }
            ]
        }
        count = sync_dag_runs("portfolio_etl_dag", limit=10)
        assert count == 1
        assert DAGRun.objects.count() == 1
        run = DAGRun.objects.first()
        assert run.state == "success"
        assert run.dag_id == "portfolio_etl_dag"

    @patch("apps.etl_monitor.services._airflow_get")
    def test_sync_failed_run_creates_alert(self, mock_get):
        mock_get.return_value = {
            "dag_runs": [
                {
                    "dag_run_id": "scheduled__2024-06-20",
                    "state": "failed",
                    "execution_date": "2024-06-20T18:30:00+00:00",
                    "end_date": "2024-06-20T18:35:00+00:00",
                    "conf": {},
                }
            ]
        }
        sync_dag_runs("portfolio_etl_dag")
        assert PipelineAlert.objects.count() == 1
        alert = PipelineAlert.objects.first()
        assert alert.severity == "CRITICAL"
        assert alert.dag_id == "portfolio_etl_dag"

    @patch("apps.etl_monitor.services._airflow_get")
    def test_sync_upserts_existing(self, mock_get):
        DAGRun.objects.create(
            dag_id="test_dag", dag_run_id="run-1",
            state="running",
            execution_date="2024-06-20T18:30:00+00:00",
        )
        mock_get.return_value = {
            "dag_runs": [
                {
                    "dag_run_id": "run-1",
                    "state": "success",
                    "execution_date": "2024-06-20T18:30:00+00:00",
                    "start_date": "2024-06-20T18:30:00+00:00",
                    "end_date": "2024-06-20T19:00:00+00:00",
                    "conf": {},
                }
            ]
        }
        sync_dag_runs("test_dag")
        assert DAGRun.objects.count() == 1
        assert DAGRun.objects.first().state == "success"

    @patch("apps.etl_monitor.services._airflow_get")
    def test_sync_empty_response(self, mock_get):
        mock_get.return_value = {"dag_runs": []}
        count = sync_dag_runs("test_dag")
        assert count == 0

    @patch("apps.etl_monitor.services._airflow_get")
    def test_sync_calculates_duration(self, mock_get):
        mock_get.return_value = {
            "dag_runs": [
                {
                    "dag_run_id": "run-dur",
                    "state": "success",
                    "execution_date": "2024-06-20T18:30:00+00:00",
                    "start_date": "2024-06-20T18:30:00+00:00",
                    "end_date": "2024-06-20T18:35:00+00:00",
                    "conf": {},
                }
            ]
        }
        sync_dag_runs("test_dag")
        run = DAGRun.objects.first()
        assert run.duration_seconds == 300.0


@pytest.mark.django_db
class TestTriggerDag:
    @patch("apps.etl_monitor.services.AIRFLOW_SESSION")
    def test_trigger_dag_success(self, mock_session):
        mock_response = MagicMock()
        mock_response.json.return_value = {"dag_run_id": "manual__new"}
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        result = trigger_dag("portfolio_etl_dag")
        assert result["dag_run_id"] == "manual__new"
        mock_session.post.assert_called_once()

    @patch("apps.etl_monitor.services.AIRFLOW_SESSION")
    def test_trigger_dag_with_conf(self, mock_session):
        mock_response = MagicMock()
        mock_response.json.return_value = {"dag_run_id": "manual__conf"}
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        trigger_dag("test_dag", conf={"key": "value"})
        call_kwargs = mock_session.post.call_args
        assert call_kwargs.kwargs["json"]["conf"] == {"key": "value"}


class TestListDags:
    @patch("apps.etl_monitor.services._airflow_get")
    def test_list_dags(self, mock_get):
        mock_get.return_value = {
            "dags": [
                {"dag_id": "portfolio_etl_dag"},
                {"dag_id": "market_data_dag"},
            ]
        }
        result = list_dags()
        assert len(result) == 2
        mock_get.assert_called_once_with("/dags", only_active=True)
