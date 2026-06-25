import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def unauthenticated_api_client():
    return APIClient()


@pytest.mark.django_db
class TestClientViewSet:
    def test_list_clients(self, api_client, client_obj):
        response = api_client.get("/api/v1/accounts/clients/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_retrieve_client(self, api_client, client_obj):
        response = api_client.get(f"/api/v1/accounts/clients/{client_obj.pk}/")
        assert response.status_code == 200
        assert response.data["client_id"] == "XYZ-001"

    def test_search_by_name(self, api_client, client_obj, second_client):
        response = api_client.get("/api/v1/accounts/clients/?search=John")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == "John Doe"

    def test_aum_summary(self, api_client, client_obj, account):
        response = api_client.get(f"/api/v1/accounts/clients/{client_obj.pk}/aum_summary/")
        assert response.status_code == 200
        assert response.data["client_id"] == "XYZ-001"
        assert response.data["total_aum"] == 5000000.0

    def test_unauthenticated_forbidden(self, unauthenticated_api_client, client_obj):
        response = unauthenticated_api_client.get("/api/v1/accounts/clients/")
        assert response.status_code == 403

    def test_ordering_by_name(self, api_client, client_obj, second_client):
        response = api_client.get("/api/v1/accounts/clients/?ordering=name")
        assert response.status_code == 200
        names = [c["name"] for c in response.data["results"]]
        assert names == sorted(names)


@pytest.mark.django_db
class TestAccountViewSet:
    def test_list_accounts(self, api_client, account):
        response = api_client.get("/api/v1/accounts/accounts-list/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_filter_by_account_type(self, api_client, account, second_account):
        response = api_client.get("/api/v1/accounts/accounts-list/?account_type=DISC")
        assert response.status_code == 200
        assert all(a["account_type"] == "DISC" for a in response.data["results"])

    def test_filter_by_currency(self, api_client, account):
        response = api_client.get("/api/v1/accounts/accounts-list/?base_currency=USD")
        assert response.status_code == 200
        assert len(response.data["results"]) >= 1


@pytest.mark.django_db
class TestTransactionViewSet:
    def test_list_transactions(self, api_client, transaction):
        response = api_client.get("/api/v1/accounts/transactions/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_read_only(self, api_client, account):
        response = api_client.post(
            "/api/v1/accounts/transactions/",
            {
                "account": account.pk,
                "transaction_type": "BUY",
                "trade_date": "2024-01-01",
                "settlement_date": "2024-01-03",
                "gross_amount": "1000",
                "net_amount": "1000",
                "reference_number": "NEW-TXN",
            },
        )
        assert response.status_code == 405

    def test_filter_by_type(self, api_client, transaction):
        response = api_client.get("/api/v1/accounts/transactions/?transaction_type=BUY")
        assert response.status_code == 200
        assert all(t["transaction_type"] == "BUY" for t in response.data["results"])
