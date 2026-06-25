import pytest
from django.urls import reverse, resolve, NoReverseMatch


class TestAccountURLs:
    def test_client_list_url(self):
        url = reverse("accounts:client_list")
        assert url == "/clients/"

    def test_client_detail_url(self):
        url = reverse("accounts:client_detail", args=[1])
        assert url == "/clients/1/"

    def test_account_detail_url(self):
        url = reverse("accounts:account_detail", args=["ACC-10001"])
        assert url == "/clients/account/ACC-10001/"

    def test_client_list_resolves(self):
        match = resolve("/clients/")
        assert match.url_name == "client_list"

    def test_client_detail_resolves(self):
        match = resolve("/clients/1/")
        assert match.url_name == "client_detail"


class TestPortfolioURLs:
    def test_dashboard_url(self):
        url = reverse("portfolio:dashboard")
        assert url == "/"

    def test_snapshot_api_url(self):
        url = reverse("portfolio:snapshot_api")
        assert url == "/api/snapshot/"


class TestAnalyticsURLs:
    def test_dashboard_url(self):
        url = reverse("analytics:dashboard")
        assert url == "/analytics/"

    def test_risk_metrics_url(self):
        url = reverse("analytics:risk_metrics")
        assert url == "/analytics/risk/"

    def test_market_data_api_url(self):
        url = reverse("analytics:market_data_api", args=["AAPL"])
        assert url == "/analytics/market-data/AAPL/"


class TestETLMonitorURLs:
    def test_dashboard_url(self):
        url = reverse("etl_monitor:dashboard")
        assert url == "/etl/"

    def test_dag_run_list_url(self):
        url = reverse("etl_monitor:dag_run_list")
        assert url == "/etl/runs/"

    def test_trigger_dag_url(self):
        url = reverse("etl_monitor:trigger_dag", args=["portfolio_etl_dag"])
        assert url == "/etl/trigger/portfolio_etl_dag/"

    def test_alerts_api_url(self):
        url = reverse("etl_monitor:alerts_api")
        assert url == "/etl/api/alerts/"


class TestAuthURLs:
    def test_login_url(self):
        url = reverse("login")
        assert url == "/accounts/login/"

    def test_logout_url(self):
        url = reverse("logout")
        assert url == "/accounts/logout/"


class TestAdminURL:
    def test_admin_url(self):
        url = reverse("admin:index")
        assert "/admin/" in url
