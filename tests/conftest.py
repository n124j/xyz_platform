from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.utils import timezone

from apps.accounts.models import Account, Client, Holding, Transaction
from apps.analytics.models import BenchmarkReturn, MarketData, RiskMetric
from apps.etl_monitor.models import DAGRun, PipelineAlert, TaskInstance
from apps.portfolio.models import AssetAllocationTarget, PortfolioSnapshot


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="testpass123", email="test@xyz.com")


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        username="staffuser",
        password="testpass123",
        email="staff@xyz.com",
        is_staff=True,
    )


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(username="admin", password="adminpass123", email="admin@xyz.com")


@pytest.fixture
def client_obj(db, staff_user):
    return Client.objects.create(
        client_id="XYZ-001",
        name="John Doe",
        email="john.doe@example.com",
        phone="+1-212-555-0100",
        tier="UHNW",
        relationship_manager=staff_user,
        onboarded_date=date(2023, 1, 15),
        kyc_verified=True,
        kyc_verified_date=date(2023, 1, 20),
        risk_profile="MODERATE",
        country="United States",
    )


@pytest.fixture
def second_client(db):
    return Client.objects.create(
        client_id="XYZ-002",
        name="Jane Smith",
        email="jane.smith@example.com",
        tier="HNW",
        onboarded_date=date(2023, 6, 1),
        risk_profile="CONSERVATIVE",
    )


@pytest.fixture
def account(db, client_obj):
    return Account.objects.create(
        account_number="ACC-10001",
        client=client_obj,
        account_type="DISC",
        inception_date=date(2023, 2, 1),
        benchmark="S&P 500",
        base_currency="USD",
        market_value=Decimal("5000000.00"),
        cash_balance=Decimal("250000.00"),
        ytd_return=Decimal("0.0825"),
    )


@pytest.fixture
def second_account(db, client_obj):
    return Account.objects.create(
        account_number="ACC-10002",
        client=client_obj,
        account_type="ADV",
        inception_date=date(2023, 3, 1),
        market_value=Decimal("2000000.00"),
        cash_balance=Decimal("100000.00"),
        ytd_return=Decimal("0.0650"),
    )


@pytest.fixture
def holding(db, account):
    return Holding.objects.create(
        account=account,
        ticker="AAPL",
        security_name="Apple Inc.",
        asset_class="EQ",
        quantity=Decimal("1000.000000"),
        cost_basis=Decimal("150.0000"),
        market_price=Decimal("185.5000"),
        market_value=Decimal("185500.00"),
        unrealized_pnl=Decimal("35500.00"),
        weight=Decimal("0.0371"),
    )


@pytest.fixture
def second_holding(db, account):
    return Holding.objects.create(
        account=account,
        ticker="MSFT",
        security_name="Microsoft Corp.",
        asset_class="EQ",
        quantity=Decimal("500.000000"),
        cost_basis=Decimal("300.0000"),
        market_price=Decimal("420.0000"),
        market_value=Decimal("210000.00"),
        unrealized_pnl=Decimal("60000.00"),
        weight=Decimal("0.0420"),
    )


@pytest.fixture
def transaction(db, account):
    return Transaction.objects.create(
        account=account,
        transaction_type="BUY",
        ticker="AAPL",
        security_name="Apple Inc.",
        trade_date=date(2024, 1, 15),
        settlement_date=date(2024, 1, 17),
        quantity=Decimal("100.000000"),
        price=Decimal("185.5000"),
        gross_amount=Decimal("18550.00"),
        fees=Decimal("9.95"),
        net_amount=Decimal("18559.95"),
        currency="USD",
        reference_number="TXN-2024-0001",
    )


@pytest.fixture
def portfolio_snapshot(db):
    return PortfolioSnapshot.objects.create(
        snapshot_date=date(2024, 6, 20),
        total_aum=Decimal("500000000.00"),
        equity_value=Decimal("300000000.00"),
        fixed_income_value=Decimal("125000000.00"),
        alternatives_value=Decimal("50000000.00"),
        cash_value=Decimal("25000000.00"),
        daily_pnl=Decimal("1250000.00"),
        daily_return_pct=Decimal("0.0025"),
        ytd_return_pct=Decimal("0.0825"),
        client_count=42,
        account_count=87,
    )


@pytest.fixture
def asset_allocation_target(db):
    return AssetAllocationTarget.objects.create(
        risk_profile="MODERATE",
        equity_target_pct=Decimal("60.00"),
        fixed_income_target_pct=Decimal("25.00"),
        alternatives_target_pct=Decimal("10.00"),
        cash_target_pct=Decimal("5.00"),
        rebalance_threshold_pct=Decimal("5.00"),
        effective_date=date(2024, 1, 1),
    )


@pytest.fixture
def market_data(db):
    return MarketData.objects.create(
        ticker="AAPL",
        security_name="Apple Inc.",
        price_date=date(2024, 6, 20),
        open_price=Decimal("184.0000"),
        high_price=Decimal("186.5000"),
        low_price=Decimal("183.2000"),
        close_price=Decimal("185.5000"),
        adjusted_close=Decimal("185.5000"),
        volume=52000000,
        currency="USD",
        source="INTERNAL",
    )


@pytest.fixture
def risk_metric(db):
    return RiskMetric.objects.create(
        scope="PORTFOLIO",
        reference_id="TOTAL",
        calculation_date=date(2024, 6, 20),
        var_95_1d=Decimal("-0.0152"),
        var_99_1d=Decimal("-0.0234"),
        cvar_95_1d=Decimal("-0.0198"),
        annualised_return=Decimal("0.0825"),
        annualised_volatility=Decimal("0.1450"),
        sharpe_ratio=Decimal("1.2500"),
        sortino_ratio=Decimal("1.7500"),
        max_drawdown=Decimal("-0.0850"),
        beta=Decimal("0.9500"),
        alpha=Decimal("0.0120"),
        information_ratio=Decimal("0.4500"),
        tracking_error=Decimal("0.0350"),
        lookback_days=252,
    )


@pytest.fixture
def benchmark_return(db):
    return BenchmarkReturn.objects.create(
        benchmark_code="SPX",
        benchmark_name="S&P 500",
        return_date=date(2024, 6, 20),
        daily_return=Decimal("0.003500"),
        cumulative_return=Decimal("0.142500"),
        index_level=Decimal("5450.0000"),
    )


@pytest.fixture
def dag_run(db):
    return DAGRun.objects.create(
        dag_id="portfolio_etl_dag",
        dag_run_id="scheduled__2024-06-20T23:30:00+00:00",
        run_type="scheduled",
        state="success",
        execution_date=timezone.now() - timedelta(hours=2),
        start_date=timezone.now() - timedelta(hours=2),
        end_date=timezone.now() - timedelta(hours=1, minutes=30),
        duration_seconds=1800.0,
    )


@pytest.fixture
def failed_dag_run(db):
    return DAGRun.objects.create(
        dag_id="market_data_dag",
        dag_run_id="scheduled__2024-06-20T14:00:00+00:00",
        run_type="scheduled",
        state="failed",
        execution_date=timezone.now() - timedelta(hours=5),
        start_date=timezone.now() - timedelta(hours=5),
        end_date=timezone.now() - timedelta(hours=4, minutes=55),
        duration_seconds=300.0,
    )


@pytest.fixture
def task_instance(db, dag_run):
    return TaskInstance.objects.create(
        dag_run=dag_run,
        task_id="extract_holdings",
        state="success",
        start_date=timezone.now() - timedelta(hours=2),
        end_date=timezone.now() - timedelta(hours=1, minutes=50),
        duration_seconds=600.0,
        try_number=1,
    )


@pytest.fixture
def pipeline_alert(db, failed_dag_run):
    return PipelineAlert.objects.create(
        dag_run=failed_dag_run,
        dag_id="market_data_dag",
        severity="CRITICAL",
        message="DAG run scheduled__2024-06-20T14:00:00+00:00 failed",
    )


@pytest.fixture
def authenticated_client(client, user):
    client.login(username="testuser", password="testpass123")
    return client
