import pytest
import json
from decimal import Decimal
from datetime import date
from django.urls import reverse
from apps.portfolio.models import PortfolioSnapshot


@pytest.mark.django_db
class TestPortfolioDashboardView:
    def test_redirects_unauthenticated(self, client):
        response = client.get(reverse("portfolio:dashboard"))
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_renders_dashboard(self, authenticated_client, portfolio_snapshot):
        response = authenticated_client.get(reverse("portfolio:dashboard"))
        assert response.status_code == 200

    def test_context_includes_snapshot(self, authenticated_client, portfolio_snapshot):
        response = authenticated_client.get(reverse("portfolio:dashboard"))
        assert response.context["snapshot"] == portfolio_snapshot

    def test_context_includes_counts(self, authenticated_client, client_obj, account):
        response = authenticated_client.get(reverse("portfolio:dashboard"))
        assert response.context["client_count"] >= 0
        assert response.context["account_count"] >= 0

    def test_context_no_snapshot(self, authenticated_client):
        response = authenticated_client.get(reverse("portfolio:dashboard"))
        assert response.status_code == 200
        assert response.context["snapshot"] is None


@pytest.mark.django_db
class TestPortfolioSnapshotAPIView:
    def test_redirects_unauthenticated(self, client):
        response = client.get(reverse("portfolio:snapshot_api"))
        assert response.status_code == 302

    def test_returns_json(self, authenticated_client, portfolio_snapshot):
        response = authenticated_client.get(reverse("portfolio:snapshot_api"))
        assert response.status_code == 200
        data = json.loads(response.content)
        assert "series" in data
        assert len(data["series"]) == 1

    def test_respects_days_parameter(self, authenticated_client):
        for i in range(5):
            PortfolioSnapshot.objects.create(
                snapshot_date=date(2024, 6, 15 + i),
                total_aum=Decimal("100000000") + i * 1000000,
            )
        response = authenticated_client.get(reverse("portfolio:snapshot_api") + "?days=3")
        data = json.loads(response.content)
        assert len(data["series"]) <= 3

    def test_series_format(self, authenticated_client, portfolio_snapshot):
        response = authenticated_client.get(reverse("portfolio:snapshot_api"))
        data = json.loads(response.content)
        entry = data["series"][0]
        assert "date" in entry
        assert "aum" in entry
        assert "daily_return" in entry
        assert "ytd_return" in entry

    def test_series_ordered_chronologically(self, authenticated_client):
        PortfolioSnapshot.objects.create(
            snapshot_date=date(2024, 6, 18), total_aum=Decimal("100"))
        PortfolioSnapshot.objects.create(
            snapshot_date=date(2024, 6, 20), total_aum=Decimal("200"))
        PortfolioSnapshot.objects.create(
            snapshot_date=date(2024, 6, 19), total_aum=Decimal("150"))
        response = authenticated_client.get(reverse("portfolio:snapshot_api"))
        data = json.loads(response.content)
        dates = [e["date"] for e in data["series"]]
        assert dates == sorted(dates)
