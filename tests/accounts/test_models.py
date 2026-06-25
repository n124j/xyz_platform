import pytest
from decimal import Decimal
from datetime import date
from django.db import IntegrityError
from apps.accounts.models import Client, Account, Holding, Transaction, ClientTier, AccountType, AssetClass


@pytest.mark.django_db
class TestClientModel:
    def test_create_client(self, client_obj):
        assert client_obj.client_id == "XYZ-001"
        assert client_obj.name == "John Doe"
        assert client_obj.tier == "UHNW"
        assert client_obj.is_active is True

    def test_str_representation(self, client_obj):
        assert "XYZ-001" in str(client_obj)
        assert "John Doe" in str(client_obj)

    def test_unique_client_id(self, client_obj):
        with pytest.raises(IntegrityError):
            Client.objects.create(
                client_id="XYZ-001",
                name="Duplicate",
                email="dup@example.com",
                onboarded_date=date(2024, 1, 1),
            )

    def test_unique_email(self, client_obj):
        with pytest.raises(IntegrityError):
            Client.objects.create(
                client_id="XYZ-999",
                name="Another",
                email="john.doe@example.com",
                onboarded_date=date(2024, 1, 1),
            )

    def test_total_aum_single_account(self, client_obj, account):
        assert client_obj.total_aum == Decimal("5000000.00")

    def test_total_aum_multiple_accounts(self, client_obj, account, second_account):
        assert client_obj.total_aum == Decimal("7000000.00")

    def test_total_aum_excludes_inactive(self, client_obj, account):
        account.is_active = False
        account.save()
        assert client_obj.total_aum == 0

    def test_total_aum_no_accounts(self, client_obj):
        assert client_obj.total_aum == 0

    def test_default_risk_profile(self, db):
        c = Client.objects.create(
            client_id="XYZ-DEF",
            name="Default",
            email="default@example.com",
            onboarded_date=date(2024, 1, 1),
        )
        assert c.risk_profile == "MODERATE"

    def test_ordering(self, client_obj, second_client):
        clients = list(Client.objects.all())
        assert clients[0].name <= clients[1].name

    def test_tier_choices(self):
        assert len(ClientTier.choices) == 4
        values = [c[0] for c in ClientTier.choices]
        assert "UHNW" in values
        assert "HNW" in values


@pytest.mark.django_db
class TestAccountModel:
    def test_create_account(self, account):
        assert account.account_number == "ACC-10001"
        assert account.account_type == "DISC"
        assert account.market_value == Decimal("5000000.00")

    def test_str_representation(self, account):
        assert "ACC-10001" in str(account)
        assert "John Doe" in str(account)

    def test_unique_account_number(self, account, client_obj):
        with pytest.raises(IntegrityError):
            Account.objects.create(
                account_number="ACC-10001",
                client=client_obj,
                account_type="ADV",
                inception_date=date(2024, 1, 1),
            )

    def test_ordering_by_market_value_desc(self, account, second_account):
        accounts = list(Account.objects.all())
        assert accounts[0].market_value >= accounts[1].market_value

    def test_default_values(self, db, client_obj):
        acc = Account.objects.create(
            account_number="ACC-DEFAULT",
            client=client_obj,
            account_type="CUST",
            inception_date=date(2024, 1, 1),
        )
        assert acc.base_currency == "USD"
        assert acc.benchmark == "S&P 500"
        assert acc.market_value == Decimal("0.00")


@pytest.mark.django_db
class TestHoldingModel:
    def test_create_holding(self, holding):
        assert holding.ticker == "AAPL"
        assert holding.asset_class == "EQ"
        assert holding.market_value == Decimal("185500.00")

    def test_str_representation(self, holding):
        assert "AAPL" in str(holding)
        assert "ACC-10001" in str(holding)

    def test_unique_together_account_ticker(self, holding, account):
        with pytest.raises(IntegrityError):
            Holding.objects.create(
                account=account,
                ticker="AAPL",
                security_name="Apple Again",
                asset_class="EQ",
                quantity=Decimal("100"),
                cost_basis=Decimal("100"),
                market_price=Decimal("100"),
                market_value=Decimal("10000"),
                unrealized_pnl=Decimal("0"),
            )

    def test_unrealized_pnl_pct(self, holding):
        pnl_pct = holding.unrealized_pnl_pct
        expected = ((Decimal("185500") - Decimal("150000")) / Decimal("150000") * 100).quantize(Decimal("0.0001"))
        assert pnl_pct == expected

    def test_unrealized_pnl_pct_zero_cost(self, db, account):
        h = Holding.objects.create(
            account=account,
            ticker="FREE",
            security_name="Free Stock",
            asset_class="EQ",
            quantity=Decimal("0"),
            cost_basis=Decimal("0"),
            market_price=Decimal("50"),
            market_value=Decimal("0"),
            unrealized_pnl=Decimal("0"),
        )
        assert h.unrealized_pnl_pct == Decimal("0.0000")

    def test_ordering_by_market_value_desc(self, holding, second_holding):
        holdings = list(Holding.objects.filter(account=holding.account))
        assert holdings[0].market_value >= holdings[1].market_value


@pytest.mark.django_db
class TestTransactionModel:
    def test_create_transaction(self, transaction):
        assert transaction.transaction_type == "BUY"
        assert transaction.ticker == "AAPL"
        assert transaction.reference_number == "TXN-2024-0001"

    def test_str_representation(self, transaction):
        assert "TXN-2024-0001" in str(transaction)
        assert "BUY" in str(transaction)

    def test_unique_reference_number(self, transaction, account):
        with pytest.raises(IntegrityError):
            Transaction.objects.create(
                account=account,
                transaction_type="SELL",
                trade_date=date(2024, 1, 16),
                settlement_date=date(2024, 1, 18),
                gross_amount=Decimal("1000"),
                net_amount=Decimal("1000"),
                reference_number="TXN-2024-0001",
            )

    def test_ordering_by_trade_date_desc(self, db, account):
        t1 = Transaction.objects.create(
            account=account, transaction_type="BUY",
            trade_date=date(2024, 1, 10), settlement_date=date(2024, 1, 12),
            gross_amount=Decimal("1000"), net_amount=Decimal("1000"),
            reference_number="TXN-OLD",
        )
        t2 = Transaction.objects.create(
            account=account, transaction_type="SELL",
            trade_date=date(2024, 6, 15), settlement_date=date(2024, 6, 17),
            gross_amount=Decimal("2000"), net_amount=Decimal("2000"),
            reference_number="TXN-NEW",
        )
        txns = list(Transaction.objects.filter(account=account))
        assert txns[0].trade_date >= txns[-1].trade_date

    def test_nullable_quantity_and_price(self, db, account):
        t = Transaction.objects.create(
            account=account, transaction_type="FEE",
            trade_date=date(2024, 3, 1), settlement_date=date(2024, 3, 1),
            gross_amount=Decimal("500"), net_amount=Decimal("500"),
            reference_number="TXN-FEE-001",
        )
        assert t.quantity is None
        assert t.price is None
