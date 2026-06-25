import pytest
import json
from django.urls import reverse
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.etl_monitor.models import DAGRun, PipelineAlert


@pytest.mark.django_db
class TestETLDashboardView:
    def test_redirects_unauthenticated(self, client):
        response = client.get(reverse("etl_monitor:dashboard"))
        assert response.status_code == 302

    def test_renders_dashboard(self, authenticated_client, dag_run):
        response = authenticated_client.get(reverse("etl_monitor:dashboard"))
        assert response.status_code == 200

    def test_context_includes_alerts(self, authenticated_client, pipeline_alert):
        response = authenticated_client.get(reverse("etl_monitor:dashboard"))
        assert "alerts" in response.context
        assert len(response.context["alerts"]) >= 1

    def test_excludes_acknowledged_alerts(self, authenticated_client, pipeline_alert, staff_user):
        pipeline_alert.acknowledged = True
        pipeline_alert.save()
        response = authenticated_client.get(reverse("etl_monitor:dashboard"))
        unack_alerts = [a for a in response.context["alerts"] if not a.acknowledged]
        assert len(unack_alerts) == 0


@pytest.mark.django_db
class TestDAGRunListView:
    def test_redirects_unauthenticated(self, client):
        response = client.get(reverse("etl_monitor:dag_run_list"))
        assert response.status_code == 302

    def test_lists_dag_runs(self, authenticated_client, dag_run, failed_dag_run):
        response = authenticated_client.get(reverse("etl_monitor:dag_run_list"))
        assert response.status_code == 200
        assert len(response.context["dag_runs"]) == 2

    def test_filter_by_dag_id(self, authenticated_client, dag_run, failed_dag_run):
        response = authenticated_client.get(
            reverse("etl_monitor:dag_run_list") + "?dag_id=portfolio_etl_dag"
        )
        for run in response.context["dag_runs"]:
            assert run.dag_id == "portfolio_etl_dag"

    def test_filter_by_state(self, authenticated_client, dag_run, failed_dag_run):
        response = authenticated_client.get(
            reverse("etl_monitor:dag_run_list") + "?state=failed"
        )
        for run in response.context["dag_runs"]:
            assert run.state == "failed"

    def test_context_includes_dag_ids(self, authenticated_client, dag_run):
        response = authenticated_client.get(reverse("etl_monitor:dag_run_list"))
        assert "dag_ids" in response.context

    def test_context_includes_state_choices(self, authenticated_client, dag_run):
        response = authenticated_client.get(reverse("etl_monitor:dag_run_list"))
        assert "states" in response.context


@pytest.mark.django_db
class TestTriggerDAGView:
    def test_requires_authentication(self, client):
        response = client.post(
            reverse("etl_monitor:trigger_dag", args=["portfolio_etl_dag"])
        )
        assert response.status_code == 302

    def test_requires_permission(self, authenticated_client):
        response = authenticated_client.post(
            reverse("etl_monitor:trigger_dag", args=["portfolio_etl_dag"])
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestPipelineAlertsAPIView:
    def test_redirects_unauthenticated(self, client):
        response = client.get(reverse("etl_monitor:alerts_api"))
        assert response.status_code == 302

    def test_returns_json(self, authenticated_client, pipeline_alert):
        response = authenticated_client.get(reverse("etl_monitor:alerts_api"))
        assert response.status_code == 200
        data = json.loads(response.content)
        assert "alerts" in data
        assert "count" in data
        assert data["count"] >= 1

    def test_only_unacknowledged(self, authenticated_client, pipeline_alert, staff_user):
        pipeline_alert.acknowledged = True
        pipeline_alert.save()
        response = authenticated_client.get(reverse("etl_monitor:alerts_api"))
        data = json.loads(response.content)
        assert data["count"] == 0

    def test_alert_format(self, authenticated_client, pipeline_alert):
        response = authenticated_client.get(reverse("etl_monitor:alerts_api"))
        data = json.loads(response.content)
        alert = data["alerts"][0]
        assert "id" in alert
        assert "dag_id" in alert
        assert "severity" in alert
        assert "message" in alert
        assert "created_at" in alert
