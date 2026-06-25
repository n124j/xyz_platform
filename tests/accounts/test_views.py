import pytest
from django.urls import reverse
from apps.accounts.models import Client


@pytest.mark.django_db
class TestClientListView:
    def test_redirects_unauthenticated(self, client):
        response = client.get(reverse("accounts:client_list"))
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_lists_active_clients(self, authenticated_client, client_obj, second_client):
        response = authenticated_client.get(reverse("accounts:client_list"))
        assert response.status_code == 200
        assert "John Doe" in response.content.decode()
        assert "Jane Smith" in response.content.decode()

    def test_excludes_inactive_clients(self, authenticated_client, client_obj):
        client_obj.is_active = False
        client_obj.save()
        response = authenticated_client.get(reverse("accounts:client_list"))
        assert response.status_code == 200
        assert "John Doe" not in response.content.decode()

    def test_search_by_name(self, authenticated_client, client_obj, second_client):
        response = authenticated_client.get(reverse("accounts:client_list") + "?q=John")
        assert response.status_code == 200
        assert "John Doe" in response.content.decode()
        assert "Jane Smith" not in response.content.decode()

    def test_search_by_client_id(self, authenticated_client, client_obj):
        response = authenticated_client.get(reverse("accounts:client_list") + "?q=XYZ-001")
        assert response.status_code == 200
        assert "John Doe" in response.content.decode()

    def test_filter_by_tier(self, authenticated_client, client_obj, second_client):
        response = authenticated_client.get(reverse("accounts:client_list") + "?tier=UHNW")
        assert response.status_code == 200
        assert "John Doe" in response.content.decode()
        assert "Jane Smith" not in response.content.decode()

    def test_context_contains_total_aum(self, authenticated_client, client_obj, account):
        response = authenticated_client.get(reverse("accounts:client_list"))
        assert "total_aum" in response.context

    def test_context_contains_tiers(self, authenticated_client, client_obj):
        response = authenticated_client.get(reverse("accounts:client_list"))
        assert "tiers" in response.context


@pytest.mark.django_db
class TestClientDetailView:
    def test_redirects_unauthenticated(self, client, client_obj):
        response = client.get(reverse("accounts:client_detail", args=[client_obj.pk]))
        assert response.status_code == 302

    def test_shows_client_detail(self, authenticated_client, client_obj):
        response = authenticated_client.get(reverse("accounts:client_detail", args=[client_obj.pk]))
        assert response.status_code == 200
        assert "John Doe" in response.content.decode()

    def test_context_includes_accounts(self, authenticated_client, client_obj, account):
        response = authenticated_client.get(reverse("accounts:client_detail", args=[client_obj.pk]))
        assert "accounts" in response.context
        assert len(response.context["accounts"]) == 1

    def test_context_includes_recent_transactions(self, authenticated_client, client_obj, account, transaction):
        response = authenticated_client.get(reverse("accounts:client_detail", args=[client_obj.pk]))
        assert "recent_transactions" in response.context

    def test_404_for_nonexistent(self, authenticated_client):
        response = authenticated_client.get(reverse("accounts:client_detail", args=[99999]))
        assert response.status_code == 404


@pytest.mark.django_db
class TestAccountDetailView:
    def test_redirects_unauthenticated(self, client, account):
        response = client.get(reverse("accounts:account_detail", args=[account.account_number]))
        assert response.status_code == 302

    def test_shows_account_detail(self, authenticated_client, account):
        response = authenticated_client.get(reverse("accounts:account_detail", args=[account.account_number]))
        assert response.status_code == 200
        assert "ACC-10001" in response.content.decode()

    def test_context_includes_holdings(self, authenticated_client, account, holding):
        response = authenticated_client.get(reverse("accounts:account_detail", args=[account.account_number]))
        assert "holdings" in response.context
        assert len(response.context["holdings"]) == 1

    def test_context_includes_transactions(self, authenticated_client, account, transaction):
        response = authenticated_client.get(reverse("accounts:account_detail", args=[account.account_number]))
        assert "transactions" in response.context

    def test_404_for_nonexistent(self, authenticated_client):
        response = authenticated_client.get(reverse("accounts:account_detail", args=["NONEXIST"]))
        assert response.status_code == 404
