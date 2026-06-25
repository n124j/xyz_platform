from datetime import date
from decimal import Decimal

import pytest

from apps.analytics.models import PerformanceAttribution
from apps.analytics.serializers import (
    BenchmarkReturnSerializer,
    MarketDataSerializer,
    PerformanceAttributionSerializer,
    RiskMetricSerializer,
)


@pytest.mark.django_db
class TestMarketDataSerializer:
    def test_serializes_all_fields(self, market_data):
        serializer = MarketDataSerializer(market_data)
        data = serializer.data
        assert data["ticker"] == "AAPL"
        assert data["volume"] == 52000000
        assert "close_price" in data
        assert "adjusted_close" in data


@pytest.mark.django_db
class TestRiskMetricSerializer:
    def test_serializes_all_fields(self, risk_metric):
        serializer = RiskMetricSerializer(risk_metric)
        data = serializer.data
        assert data["scope"] == "PORTFOLIO"
        assert "var_95_1d" in data
        assert "sharpe_ratio" in data
        assert "max_drawdown" in data


@pytest.mark.django_db
class TestBenchmarkReturnSerializer:
    def test_serializes_all_fields(self, benchmark_return):
        serializer = BenchmarkReturnSerializer(benchmark_return)
        data = serializer.data
        assert data["benchmark_code"] == "SPX"
        assert "daily_return" in data
        assert "index_level" in data


@pytest.mark.django_db
class TestPerformanceAttributionSerializer:
    def test_serializes_all_fields(self, db):
        pa = PerformanceAttribution.objects.create(
            account_number="ACC-001",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 6, 30),
            asset_class="EQ",
            allocation_effect=Decimal("0.0025"),
            selection_effect=Decimal("0.0032"),
            interaction_effect=Decimal("0.0008"),
            total_effect=Decimal("0.0065"),
        )
        serializer = PerformanceAttributionSerializer(pa)
        data = serializer.data
        assert data["account_number"] == "ACC-001"
        assert "allocation_effect" in data
        assert "total_effect" in data
