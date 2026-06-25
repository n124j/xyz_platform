import json
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.analytics.models import MarketData, RiskMetric


@pytest.mark.django_db
class TestAnalyticsDashboardView:
    def test_redirects_unauthenticated(self, client):
        response = client.get(reverse("analytics:dashboard"))
        assert response.status_code == 302

    def test_renders_dashboard(self, authenticated_client, risk_metric):
        response = authenticated_client.get(reverse("analytics:dashboard"))
        assert response.status_code == 200

    def test_context_with_portfolio_risk(self, authenticated_client, risk_metric):
        response = authenticated_client.get(reverse("analytics:dashboard"))
        assert response.context["portfolio_risk"] is not None
        assert "kpi_var95" in response.context
        assert "kpi_sharpe" in response.context
        assert "kpi_maxdd" in response.context
        assert "kpi_vol" in response.context

    def test_context_without_risk_data(self, authenticated_client):
        response = authenticated_client.get(reverse("analytics:dashboard"))
        assert response.status_code == 200
        assert response.context["portfolio_risk"] is None

    def test_context_includes_risk_metrics_json(self, authenticated_client, risk_metric):
        response = authenticated_client.get(reverse("analytics:dashboard"))
        metrics_json = response.context["risk_metrics_json"]
        metrics = json.loads(metrics_json)
        assert isinstance(metrics, list)
        assert len(metrics) >= 1


@pytest.mark.django_db
class TestRiskMetricListView:
    def test_redirects_unauthenticated(self, client):
        response = client.get(reverse("analytics:risk_metrics"))
        assert response.status_code == 302

    def test_lists_risk_metrics(self, authenticated_client, risk_metric):
        response = authenticated_client.get(reverse("analytics:risk_metrics"))
        assert response.status_code == 200
        assert len(response.context["risk_metrics"]) == 1

    def test_filter_by_scope(self, authenticated_client, risk_metric):
        RiskMetric.objects.create(
            scope="ACCOUNT",
            reference_id="ACC-001",
            calculation_date=date(2024, 6, 20),
        )
        response = authenticated_client.get(reverse("analytics:risk_metrics") + "?scope=PORTFOLIO")
        assert response.status_code == 200
        for rm in response.context["risk_metrics"]:
            assert rm.scope == "PORTFOLIO"

    def test_no_filter_shows_all(self, authenticated_client, risk_metric):
        RiskMetric.objects.create(
            scope="ACCOUNT",
            reference_id="ACC-001",
            calculation_date=date(2024, 6, 20),
        )
        response = authenticated_client.get(reverse("analytics:risk_metrics"))
        assert len(response.context["risk_metrics"]) == 2


@pytest.mark.django_db
class TestMarketDataAPIView:
    def test_redirects_unauthenticated(self, client):
        response = client.get(reverse("analytics:market_data_api", args=["AAPL"]))
        assert response.status_code == 302

    def test_returns_json(self, authenticated_client, market_data):
        response = authenticated_client.get(reverse("analytics:market_data_api", args=["AAPL"]))
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["ticker"] == "AAPL"
        assert "data" in data

    def test_uppercase_ticker(self, authenticated_client, market_data):
        response = authenticated_client.get(reverse("analytics:market_data_api", args=["aapl"]))
        data = json.loads(response.content)
        assert data["ticker"] == "AAPL"

    def test_data_format(self, authenticated_client, market_data):
        response = authenticated_client.get(reverse("analytics:market_data_api", args=["AAPL"]))
        data = json.loads(response.content)
        if data["data"]:
            entry = data["data"][0]
            assert "date" in entry
            assert "close" in entry
            assert "volume" in entry

    def test_empty_for_unknown_ticker(self, authenticated_client):
        response = authenticated_client.get(reverse("analytics:market_data_api", args=["ZZZZ"]))
        data = json.loads(response.content)
        assert data["data"] == []

    def test_respects_days_parameter(self, authenticated_client):
        today = date.today()
        for i in range(10):
            MarketData.objects.create(
                ticker="TEST",
                security_name="Test",
                price_date=today - timedelta(days=10 - i),
                open_price=Decimal("100"),
                high_price=Decimal("100"),
                low_price=Decimal("100"),
                close_price=Decimal("100"),
                adjusted_close=Decimal("100"),
            )
        response = authenticated_client.get(reverse("analytics:market_data_api", args=["TEST"]) + "?days=365")
        data = json.loads(response.content)
        assert len(data["data"]) == 10
