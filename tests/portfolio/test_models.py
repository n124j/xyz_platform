import pytest
from decimal import Decimal
from datetime import date
from django.db import IntegrityError
from apps.portfolio.models import PortfolioSnapshot, AssetAllocationTarget


@pytest.mark.django_db
class TestPortfolioSnapshotModel:
    def test_create_snapshot(self, portfolio_snapshot):
        assert portfolio_snapshot.total_aum == Decimal("500000000.00")
        assert portfolio_snapshot.client_count == 42
        assert portfolio_snapshot.account_count == 87

    def test_str_representation(self, portfolio_snapshot):
        s = str(portfolio_snapshot)
        assert "Portfolio Snapshot" in s
        assert "2024-06-20" in s

    def test_unique_snapshot_date(self, portfolio_snapshot):
        with pytest.raises(IntegrityError):
            PortfolioSnapshot.objects.create(
                snapshot_date=date(2024, 6, 20),
                total_aum=Decimal("100000000.00"),
            )

    def test_equity_weight(self, portfolio_snapshot):
        weight = portfolio_snapshot.equity_weight
        expected = 300000000.0 / 500000000.0 * 100
        assert abs(weight - expected) < 0.01

    def test_fixed_income_weight(self, portfolio_snapshot):
        weight = portfolio_snapshot.fixed_income_weight
        expected = 125000000.0 / 500000000.0 * 100
        assert abs(weight - expected) < 0.01

    def test_weight_zero_aum(self, db):
        snap = PortfolioSnapshot.objects.create(
            snapshot_date=date(2024, 1, 1),
            total_aum=Decimal("0"),
        )
        assert snap.equity_weight == 0
        assert snap.fixed_income_weight == 0

    def test_ordering_by_date_desc(self, db):
        PortfolioSnapshot.objects.create(snapshot_date=date(2024, 6, 18), total_aum=Decimal("100"))
        PortfolioSnapshot.objects.create(snapshot_date=date(2024, 6, 20), total_aum=Decimal("200"))
        PortfolioSnapshot.objects.create(snapshot_date=date(2024, 6, 19), total_aum=Decimal("150"))
        snapshots = list(PortfolioSnapshot.objects.all())
        dates = [s.snapshot_date for s in snapshots]
        assert dates == sorted(dates, reverse=True)


@pytest.mark.django_db
class TestAssetAllocationTargetModel:
    def test_create_target(self, asset_allocation_target):
        assert asset_allocation_target.risk_profile == "MODERATE"
        assert asset_allocation_target.equity_target_pct == Decimal("60.00")

    def test_str_representation(self, asset_allocation_target):
        assert "MODERATE" in str(asset_allocation_target)

    def test_unique_risk_profile(self, asset_allocation_target):
        with pytest.raises(IntegrityError):
            AssetAllocationTarget.objects.create(
                risk_profile="MODERATE",
                equity_target_pct=Decimal("50"),
                fixed_income_target_pct=Decimal("30"),
                alternatives_target_pct=Decimal("15"),
                cash_target_pct=Decimal("5"),
                effective_date=date(2024, 7, 1),
            )

    def test_default_rebalance_threshold(self, db):
        target = AssetAllocationTarget.objects.create(
            risk_profile="AGGRESSIVE",
            equity_target_pct=Decimal("80"),
            fixed_income_target_pct=Decimal("10"),
            alternatives_target_pct=Decimal("8"),
            cash_target_pct=Decimal("2"),
            effective_date=date(2024, 1, 1),
        )
        assert target.rebalance_threshold_pct == Decimal("5.00")
