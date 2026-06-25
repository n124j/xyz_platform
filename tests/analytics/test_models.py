from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.analytics.models import BenchmarkReturn, MarketData, PerformanceAttribution, RiskMetric


@pytest.mark.django_db
class TestMarketDataModel:
    def test_create_market_data(self, market_data):
        assert market_data.ticker == "AAPL"
        assert market_data.close_price == Decimal("185.5000")
        assert market_data.volume == 52000000

    def test_str_representation(self, market_data):
        s = str(market_data)
        assert "AAPL" in s
        assert "185.5" in s

    def test_unique_together_ticker_date(self, market_data):
        with pytest.raises(IntegrityError):
            MarketData.objects.create(
                ticker="AAPL",
                security_name="Apple",
                price_date=date(2024, 6, 20),
                open_price=Decimal("184"),
                high_price=Decimal("187"),
                low_price=Decimal("183"),
                close_price=Decimal("186"),
                adjusted_close=Decimal("186"),
                volume=50000000,
            )

    def test_ordering_by_date_desc(self, db):
        MarketData.objects.create(
            ticker="MSFT",
            security_name="Microsoft",
            price_date=date(2024, 6, 18),
            open_price=Decimal("400"),
            high_price=Decimal("410"),
            low_price=Decimal("398"),
            close_price=Decimal("405"),
            adjusted_close=Decimal("405"),
            volume=30000000,
        )
        MarketData.objects.create(
            ticker="MSFT",
            security_name="Microsoft",
            price_date=date(2024, 6, 20),
            open_price=Decimal("405"),
            high_price=Decimal("415"),
            low_price=Decimal("403"),
            close_price=Decimal("410"),
            adjusted_close=Decimal("410"),
            volume=32000000,
        )
        records = list(MarketData.objects.filter(ticker="MSFT"))
        assert records[0].price_date > records[1].price_date

    def test_default_values(self, db):
        md = MarketData.objects.create(
            ticker="TEST",
            security_name="Test",
            price_date=date(2024, 1, 1),
            open_price=Decimal("100"),
            high_price=Decimal("100"),
            low_price=Decimal("100"),
            close_price=Decimal("100"),
            adjusted_close=Decimal("100"),
        )
        assert md.currency == "USD"
        assert md.source == "INTERNAL"
        assert md.volume == 0


@pytest.mark.django_db
class TestRiskMetricModel:
    def test_create_risk_metric(self, risk_metric):
        assert risk_metric.scope == "PORTFOLIO"
        assert risk_metric.sharpe_ratio == Decimal("1.2500")
        assert risk_metric.lookback_days == 252

    def test_str_representation(self, risk_metric):
        s = str(risk_metric)
        assert "PORTFOLIO" in s
        assert "TOTAL" in s

    def test_unique_together(self, risk_metric):
        with pytest.raises(IntegrityError):
            RiskMetric.objects.create(
                scope="PORTFOLIO",
                reference_id="TOTAL",
                calculation_date=date(2024, 6, 20),
                lookback_days=252,
            )

    def test_nullable_fields(self, db):
        rm = RiskMetric.objects.create(
            scope="ACCOUNT",
            reference_id="ACC-001",
            calculation_date=date(2024, 6, 20),
        )
        assert rm.var_95_1d is None
        assert rm.sharpe_ratio is None
        assert rm.beta is None


@pytest.mark.django_db
class TestBenchmarkReturnModel:
    def test_create_benchmark_return(self, benchmark_return):
        assert benchmark_return.benchmark_code == "SPX"
        assert benchmark_return.index_level == Decimal("5450.0000")

    def test_str_representation(self, benchmark_return):
        assert "SPX" in str(benchmark_return)

    def test_unique_together(self, benchmark_return):
        with pytest.raises(IntegrityError):
            BenchmarkReturn.objects.create(
                benchmark_code="SPX",
                benchmark_name="S&P 500",
                return_date=date(2024, 6, 20),
                daily_return=Decimal("0.001"),
                cumulative_return=Decimal("0.1"),
                index_level=Decimal("5440"),
            )


@pytest.mark.django_db
class TestPerformanceAttributionModel:
    def test_create_attribution(self, db):
        pa = PerformanceAttribution.objects.create(
            account_number="ACC-10001",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 6, 30),
            asset_class="EQ",
            allocation_effect=Decimal("0.002500"),
            selection_effect=Decimal("0.003200"),
            interaction_effect=Decimal("0.000800"),
            total_effect=Decimal("0.006500"),
        )
        assert pa.total_effect == Decimal("0.006500")

    def test_str_representation(self, db):
        pa = PerformanceAttribution.objects.create(
            account_number="ACC-10001",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 6, 30),
            asset_class="FI",
            allocation_effect=Decimal("0.001"),
            selection_effect=Decimal("0.001"),
            interaction_effect=Decimal("0.001"),
            total_effect=Decimal("0.003"),
        )
        assert "ACC-10001" in str(pa)
