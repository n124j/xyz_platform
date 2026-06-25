import pytest
import json
from decimal import Decimal
from datetime import date
from unittest.mock import patch, MagicMock
from django.urls import reverse
from django.utils import timezone
from apps.etl_monitor.models import AdHocTaskExecution
from apps.etl_monitor.tasks import (
    ADHOC_TASK_REGISTRY,
    run_adhoc_task,
    _adhoc_sync_all_dag_runs,
    _adhoc_sync_single_dag,
    _adhoc_generate_portfolio_snapshot,
    _adhoc_purge_old_dag_runs,
    _adhoc_system_health_check,
)


@pytest.mark.django_db
class TestAdHocTaskRegistry:
    def test_registry_has_all_tasks(self):
        expected = {
            "sync_all_dag_runs", "sync_single_dag",
            "generate_portfolio_snapshot", "refresh_risk_metrics",
            "purge_old_dag_runs", "system_health_check",
        }
        assert set(ADHOC_TASK_REGISTRY.keys()) == expected

    def test_each_task_has_required_fields(self):
        for key, meta in ADHOC_TASK_REGISTRY.items():
            assert "display_name" in meta, f"{key} missing display_name"
            assert "description" in meta, f"{key} missing description"
            assert "parameters" in meta, f"{key} missing parameters"
            assert "category" in meta, f"{key} missing category"

    def test_select_parameter_has_choices(self):
        meta = ADHOC_TASK_REGISTRY["sync_single_dag"]
        dag_param = meta["parameters"]["dag_id"]
        assert dag_param["type"] == "select"
        assert len(dag_param["choices"]) == 3


@pytest.mark.django_db
class TestAdHocTaskModel:
    def test_create_execution(self, user):
        exec_obj = AdHocTaskExecution.objects.create(
            task_name="sync_all_dag_runs",
            display_name="Sync All DAG Runs",
            celery_task_id="test-123",
            parameters={},
            triggered_by=user,
        )
        assert exec_obj.status == "PENDING"
        assert exec_obj.celery_task_id == "test-123"

    def test_str_representation(self, user):
        exec_obj = AdHocTaskExecution.objects.create(
            task_name="test",
            display_name="Test Task",
            celery_task_id="test-str",
            triggered_by=user,
        )
        s = str(exec_obj)
        assert "Test Task" in s
        assert "PENDING" in s

    def test_duration_seconds(self, user):
        now = timezone.now()
        exec_obj = AdHocTaskExecution.objects.create(
            task_name="test",
            display_name="Test",
            celery_task_id="test-dur",
            triggered_by=user,
            started_at=now,
            completed_at=now + timezone.timedelta(seconds=45),
        )
        assert exec_obj.duration_seconds == 45.0

    def test_duration_display(self, user):
        now = timezone.now()
        exec_obj = AdHocTaskExecution.objects.create(
            task_name="test",
            display_name="Test",
            celery_task_id="test-dur2",
            triggered_by=user,
            started_at=now,
            completed_at=now + timezone.timedelta(seconds=125),
        )
        assert exec_obj.duration_display == "2m 5s"

    def test_duration_display_no_times(self, user):
        exec_obj = AdHocTaskExecution.objects.create(
            task_name="test",
            display_name="Test",
            celery_task_id="test-nodur",
            triggered_by=user,
        )
        assert exec_obj.duration_display == "—"

    def test_ordering(self, user):
        AdHocTaskExecution.objects.create(
            task_name="a", display_name="A", celery_task_id="order-1", triggered_by=user)
        AdHocTaskExecution.objects.create(
            task_name="b", display_name="B", celery_task_id="order-2", triggered_by=user)
        execs = list(AdHocTaskExecution.objects.all())
        assert execs[0].created_at >= execs[1].created_at


@pytest.mark.django_db
class TestAdHocTaskListView:
    def test_redirects_unauthenticated(self, client):
        response = client.get(reverse("etl_monitor:adhoc_tasks"))
        assert response.status_code == 302

    def test_renders_page(self, authenticated_client):
        response = authenticated_client.get(reverse("etl_monitor:adhoc_tasks"))
        assert response.status_code == 200
        assert "Ad-Hoc Task Runner" in response.content.decode()

    def test_context_has_categories(self, authenticated_client):
        response = authenticated_client.get(reverse("etl_monitor:adhoc_tasks"))
        assert "categories" in response.context
        assert len(response.context["categories"]) > 0

    def test_context_has_recent_executions(self, authenticated_client):
        response = authenticated_client.get(reverse("etl_monitor:adhoc_tasks"))
        assert "recent_executions" in response.context

    def test_post_unknown_task(self, authenticated_client):
        response = authenticated_client.post(reverse("etl_monitor:adhoc_tasks"), {
            "task_key": "nonexistent_task",
        })
        assert response.status_code == 302

    @patch("apps.etl_monitor.views.run_adhoc_task")
    def test_post_valid_task(self, mock_task, authenticated_client):
        mock_task.apply_async = MagicMock()
        response = authenticated_client.post(reverse("etl_monitor:adhoc_tasks"), {
            "task_key": "sync_all_dag_runs",
        })
        assert response.status_code == 302
        assert AdHocTaskExecution.objects.count() == 1
        mock_task.apply_async.assert_called_once()

    @patch("apps.etl_monitor.views.run_adhoc_task")
    def test_post_with_parameters(self, mock_task, authenticated_client):
        mock_task.apply_async = MagicMock()
        response = authenticated_client.post(reverse("etl_monitor:adhoc_tasks"), {
            "task_key": "sync_single_dag",
            "param_dag_id": "portfolio_etl_dag",
            "param_limit": "10",
        })
        assert response.status_code == 302
        exec_obj = AdHocTaskExecution.objects.first()
        assert exec_obj.parameters["dag_id"] == "portfolio_etl_dag"
        assert exec_obj.parameters["limit"] == 10

    @patch("apps.etl_monitor.views.run_adhoc_task")
    def test_post_missing_required_param(self, mock_task, authenticated_client):
        mock_task.apply_async = MagicMock()
        response = authenticated_client.post(reverse("etl_monitor:adhoc_tasks"), {
            "task_key": "sync_single_dag",
            "param_dag_id": "",
        })
        assert response.status_code == 302
        assert AdHocTaskExecution.objects.count() == 0


@pytest.mark.django_db
class TestAdHocTaskStatusView:
    def test_redirects_unauthenticated(self, client, user):
        exec_obj = AdHocTaskExecution.objects.create(
            task_name="test", display_name="Test",
            celery_task_id="status-test", triggered_by=user,
        )
        response = client.get(reverse("etl_monitor:adhoc_task_status", args=[exec_obj.pk]))
        assert response.status_code == 302

    def test_returns_json(self, authenticated_client, user):
        exec_obj = AdHocTaskExecution.objects.create(
            task_name="test", display_name="Test Task",
            celery_task_id="status-json", triggered_by=user,
            status="SUCCESS", result={"count": 5},
        )
        response = authenticated_client.get(
            reverse("etl_monitor:adhoc_task_status", args=[exec_obj.pk])
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["status"] == "SUCCESS"
        assert data["display_name"] == "Test Task"
        assert data["result"] == {"count": 5}

    def test_404_for_nonexistent(self, authenticated_client):
        response = authenticated_client.get(
            reverse("etl_monitor:adhoc_task_status", args=[99999])
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestAdHocTaskImplementations:
    @patch("apps.etl_monitor.tasks.services.sync_dag_runs")
    def test_sync_all(self, mock_sync):
        mock_sync.return_value = 5
        result = _adhoc_sync_all_dag_runs({})
        assert result["total_synced"] == 15
        assert "portfolio_etl_dag" in result["dags"]

    @patch("apps.etl_monitor.tasks.services.sync_dag_runs")
    def test_sync_single(self, mock_sync):
        mock_sync.return_value = 3
        result = _adhoc_sync_single_dag({"dag_id": "portfolio_etl_dag"})
        assert result["synced"] == 3
        assert result["dag_id"] == "portfolio_etl_dag"

    def test_sync_single_missing_dag_id(self):
        with pytest.raises(ValueError, match="dag_id is required"):
            _adhoc_sync_single_dag({})

    def test_sync_single_unknown_dag(self):
        with pytest.raises(ValueError, match="Unknown DAG"):
            _adhoc_sync_single_dag({"dag_id": "fake_dag"})

    def test_generate_portfolio_snapshot(self, client_obj, account, holding):
        result = _adhoc_generate_portfolio_snapshot({})
        assert result["status"] == "created"
        assert result["account_count"] >= 1

    def test_generate_portfolio_snapshot_already_exists(self, portfolio_snapshot):
        from apps.portfolio.models import PortfolioSnapshot
        today = timezone.now().date()
        PortfolioSnapshot.objects.update_or_create(
            snapshot_date=today,
            defaults={"total_aum": Decimal("100")},
        )
        result = _adhoc_generate_portfolio_snapshot({})
        assert result["status"] == "skipped"

    def test_purge_old_dag_runs(self, dag_run):
        from apps.etl_monitor.models import DAGRun
        old_run = DAGRun.objects.create(
            dag_id="test", dag_run_id="old-run",
            state="success",
            execution_date=timezone.now() - timezone.timedelta(days=200),
        )
        result = _adhoc_purge_old_dag_runs({"days": 90})
        assert result["deleted"] >= 1
        assert not DAGRun.objects.filter(pk=old_run.pk).exists()

    @patch("apps.etl_monitor.tasks.services.list_dags")
    def test_health_check_all_ok(self, mock_dags):
        mock_dags.return_value = [{"dag_id": "test"}]
        result = _adhoc_system_health_check({})
        assert result["healthy"] is True
        assert result["checks"]["postgresql"]["status"] == "ok"
        assert result["checks"]["redis"]["status"] == "ok"
        assert result["checks"]["airflow"]["status"] == "ok"

    @patch("apps.etl_monitor.tasks.services.list_dags")
    def test_health_check_airflow_down(self, mock_dags):
        mock_dags.side_effect = Exception("Connection refused")
        result = _adhoc_system_health_check({})
        assert result["healthy"] is False
        assert result["checks"]["airflow"]["status"] == "error"
