import pytest
from decimal import Decimal
from apps.accounts.serializers import ClientSerializer, AccountSerializer, HoldingSerializer, TransactionSerializer


@pytest.mark.django_db
class TestHoldingSerializer:
    def test_serializes_all_fields(self, holding):
        serializer = HoldingSerializer(holding)
        data = serializer.data
        assert data["ticker"] == "AAPL"
        assert data["security_name"] == "Apple Inc."
        assert data["asset_class"] == "EQ"

    def test_includes_unrealized_pnl_pct(self, holding):
        serializer = HoldingSerializer(holding)
        assert "unrealized_pnl_pct" in serializer.data


@pytest.mark.django_db
class TestTransactionSerializer:
    def test_serializes_all_fields(self, transaction):
        serializer = TransactionSerializer(transaction)
        data = serializer.data
        assert data["transaction_type"] == "BUY"
        assert data["reference_number"] == "TXN-2024-0001"


@pytest.mark.django_db
class TestAccountSerializer:
    def test_serializes_with_nested_holdings(self, account, holding):
        serializer = AccountSerializer(account)
        data = serializer.data
        assert data["account_number"] == "ACC-10001"
        assert len(data["holdings"]) == 1
        assert data["holdings"][0]["ticker"] == "AAPL"


@pytest.mark.django_db
class TestClientSerializer:
    def test_serializes_with_nested_accounts(self, client_obj, account):
        serializer = ClientSerializer(client_obj)
        data = serializer.data
        assert data["client_id"] == "XYZ-001"
        assert data["name"] == "John Doe"
        assert len(data["accounts"]) == 1

    def test_includes_total_aum(self, client_obj, account):
        serializer = ClientSerializer(client_obj)
        assert "total_aum" in serializer.data
