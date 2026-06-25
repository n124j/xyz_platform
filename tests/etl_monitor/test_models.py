import pytest
from datetime import timedelta
from django.utils import timezone
from django.db import IntegrityError
from apps.etl_monitor.models import DAGRun, TaskInstance, PipelineAlert


@pytest.mark.django_db
class TestDAGRunModel:
    def test_create_dag_run(self, dag_run):
        assert dag_run.dag_id == "portfolio_etl_dag"
        assert dag_run.state == "success"

    def test_str_representation(self, dag_run):
        s = str(dag_run)
        assert "portfolio_etl_dag" in s
        assert "success" in s

    def test_unique_dag_run_id(self, dag_run):
        with pytest.raises(IntegrityError):
            DAGRun.objects.create(
                dag_id="test_dag",
                dag_run_id=dag_run.dag_run_id,
                state="queued",
                execution_date=timezone.now(),
            )

    def test_is_healthy_success(self, dag_run):
        assert dag_run.is_healthy is True

    def test_is_healthy_failed(self, failed_dag_run):
        assert failed_dag_run.is_healthy is False

    def test_is_healthy_running(self, db):
        run = DAGRun.objects.create(
            dag_id="test", dag_run_id="test-running",
            state="running", execution_date=timezone.now(),
        )
        assert run.is_healthy is False

    def test_duration_display(self, dag_run):
        display = dag_run.duration_display
        assert "m" in display
        assert "s" in display

    def test_duration_display_no_duration(self, db):
        run = DAGRun.objects.create(
            dag_id="test", dag_run_id="test-no-dur",
            state="queued", execution_date=timezone.now(),
        )
        assert run.duration_display == "—"

    def test_ordering_by_execution_date_desc(self, dag_run, failed_dag_run):
        runs = list(DAGRun.objects.all())
        dates = [r.execution_date for r in runs]
        assert dates == sorted(dates, reverse=True)

    def test_json_conf_default(self, db):
        run = DAGRun.objects.create(
            dag_id="test", dag_run_id="test-conf",
            state="queued", execution_date=timezone.now(),
        )
        assert run.conf == {}


@pytest.mark.django_db
class TestTaskInstanceModel:
    def test_create_task_instance(self, task_instance):
        assert task_instance.task_id == "extract_holdings"
        assert task_instance.state == "success"
        assert task_instance.try_number == 1

    def test_str_representation(self, task_instance):
        s = str(task_instance)
        assert "extract_holdings" in s
        assert "success" in s

    def test_unique_together_dag_run_task_id(self, task_instance, dag_run):
        with pytest.raises(IntegrityError):
            TaskInstance.objects.create(
                dag_run=dag_run,
                task_id="extract_holdings",
                state="failed",
            )

    def test_cascade_delete(self, dag_run, task_instance):
        dag_run_id = dag_run.pk
        dag_run.delete()
        assert TaskInstance.objects.filter(dag_run_id=dag_run_id).count() == 0


@pytest.mark.django_db
class TestPipelineAlertModel:
    def test_create_alert(self, pipeline_alert):
        assert pipeline_alert.severity == "CRITICAL"
        assert pipeline_alert.acknowledged is False

    def test_str_representation(self, pipeline_alert):
        s = str(pipeline_alert)
        assert "CRITICAL" in s
        assert "market_data_dag" in s

    def test_acknowledge_alert(self, pipeline_alert, staff_user):
        pipeline_alert.acknowledged = True
        pipeline_alert.acknowledged_by = staff_user
        pipeline_alert.acknowledged_at = timezone.now()
        pipeline_alert.save()
        pipeline_alert.refresh_from_db()
        assert pipeline_alert.acknowledged is True
        assert pipeline_alert.acknowledged_by == staff_user

    def test_set_null_on_dag_run_delete(self, pipeline_alert, failed_dag_run):
        failed_dag_run.delete()
        pipeline_alert.refresh_from_db()
        assert pipeline_alert.dag_run is None

    def test_ordering_by_created_at_desc(self, pipeline_alert, db, failed_dag_run):
        alert2 = PipelineAlert.objects.create(
            dag_id="test_dag", severity="WARNING", message="Test alert",
        )
        alerts = list(PipelineAlert.objects.all())
        assert alerts[0].created_at >= alerts[1].created_at
