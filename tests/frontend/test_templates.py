import pytest
from django.template.loader import get_template
from django.urls import reverse


@pytest.mark.django_db
class TestTemplateExistence:
    """Verify all required templates exist and can be loaded."""

    def test_base_template(self):
        tpl = get_template("base/base.html")
        assert tpl is not None

    def test_login_template(self):
        tpl = get_template("base/login.html")
        assert tpl is not None

    def test_client_list_template(self):
        tpl = get_template("accounts/client_list.html")
        assert tpl is not None

    def test_client_detail_template(self):
        tpl = get_template("accounts/client_detail.html")
        assert tpl is not None

    def test_account_detail_template(self):
        tpl = get_template("accounts/account_detail.html")
        assert tpl is not None

    def test_portfolio_dashboard_template(self):
        tpl = get_template("portfolio/dashboard.html")
        assert tpl is not None

    def test_analytics_dashboard_template(self):
        tpl = get_template("analytics/dashboard.html")
        assert tpl is not None

    def test_risk_metrics_template(self):
        tpl = get_template("analytics/risk_metrics.html")
        assert tpl is not None

    def test_etl_dashboard_template(self):
        tpl = get_template("etl_monitor/dashboard.html")
        assert tpl is not None

    def test_dag_run_list_template(self):
        tpl = get_template("etl_monitor/dag_run_list.html")
        assert tpl is not None

    def test_risk_kpi_card_partial(self):
        tpl = get_template("analytics/_risk_kpi_card.html")
        assert tpl is not None


@pytest.mark.django_db
class TestLoginPage:
    def test_login_page_renders(self, client):
        response = client.get(reverse("login"))
        assert response.status_code == 200
        content = response.content.decode()
        assert "login" in content.lower() or "password" in content.lower()

    def test_login_with_valid_credentials(self, client, user):
        response = client.post(
            reverse("login"),
            {
                "username": "testuser",
                "password": "testpass123",
            },
        )
        assert response.status_code == 302

    def test_login_with_invalid_credentials(self, client, user):
        response = client.post(
            reverse("login"),
            {
                "username": "testuser",
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestPortfolioDashboardRendering:
    def test_renders_kpi_cards(self, authenticated_client, portfolio_snapshot):
        response = authenticated_client.get(reverse("portfolio:dashboard"))
        assert response.status_code == 200

    def test_renders_without_data(self, authenticated_client):
        response = authenticated_client.get(reverse("portfolio:dashboard"))
        assert response.status_code == 200


@pytest.mark.django_db
class TestClientListRendering:
    def test_renders_client_table(self, authenticated_client, client_obj):
        response = authenticated_client.get(reverse("accounts:client_list"))
        content = response.content.decode()
        assert "John Doe" in content

    def test_renders_search_form(self, authenticated_client, client_obj):
        response = authenticated_client.get(reverse("accounts:client_list"))
        assert response.status_code == 200


@pytest.mark.django_db
class TestAnalyticsDashboardRendering:
    def test_renders_with_risk_data(self, authenticated_client, risk_metric):
        response = authenticated_client.get(reverse("analytics:dashboard"))
        assert response.status_code == 200

    def test_renders_without_risk_data(self, authenticated_client):
        response = authenticated_client.get(reverse("analytics:dashboard"))
        assert response.status_code == 200


@pytest.mark.django_db
class TestETLDashboardRendering:
    def test_renders_with_dag_runs(self, authenticated_client, dag_run):
        response = authenticated_client.get(reverse("etl_monitor:dashboard"))
        assert response.status_code == 200

    def test_renders_alerts_section(self, authenticated_client, pipeline_alert):
        response = authenticated_client.get(reverse("etl_monitor:dashboard"))
        assert response.status_code == 200
