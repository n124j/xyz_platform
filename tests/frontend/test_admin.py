import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestAdminAccess:
    def test_admin_login_page(self, client):
        response = client.get(reverse("admin:login"))
        assert response.status_code == 200

    def test_admin_requires_staff(self, client, user):
        client.login(username="testuser", password="testpass123")
        response = client.get(reverse("admin:index"))
        assert response.status_code == 302

    def test_admin_accessible_by_superuser(self, client, superuser):
        client.login(username="admin", password="adminpass123")
        response = client.get(reverse("admin:index"))
        assert response.status_code == 200


@pytest.mark.django_db
class TestAdminClientCRUD:
    def test_client_changelist(self, client, superuser):
        client.login(username="admin", password="adminpass123")
        response = client.get(reverse("admin:accounts_client_changelist"))
        assert response.status_code == 200

    def test_client_add_page(self, client, superuser):
        client.login(username="admin", password="adminpass123")
        response = client.get(reverse("admin:accounts_client_add"))
        assert response.status_code == 200

    def test_account_changelist(self, client, superuser):
        client.login(username="admin", password="adminpass123")
        response = client.get(reverse("admin:accounts_account_changelist"))
        assert response.status_code == 200

    def test_holding_changelist(self, client, superuser):
        client.login(username="admin", password="adminpass123")
        response = client.get(reverse("admin:accounts_holding_changelist"))
        assert response.status_code == 200

    def test_transaction_changelist(self, client, superuser):
        client.login(username="admin", password="adminpass123")
        response = client.get(reverse("admin:accounts_transaction_changelist"))
        assert response.status_code == 200


@pytest.mark.django_db
class TestAdminAnalytics:
    def test_marketdata_changelist(self, client, superuser):
        client.login(username="admin", password="adminpass123")
        response = client.get(reverse("admin:analytics_marketdata_changelist"))
        assert response.status_code == 200

    def test_riskmetric_changelist(self, client, superuser):
        client.login(username="admin", password="adminpass123")
        response = client.get(reverse("admin:analytics_riskmetric_changelist"))
        assert response.status_code == 200


@pytest.mark.django_db
class TestAdminETLMonitor:
    def test_dagrun_changelist(self, client, superuser):
        client.login(username="admin", password="adminpass123")
        response = client.get(reverse("admin:etl_monitor_dagrun_changelist"))
        assert response.status_code == 200

    def test_pipelinealert_changelist(self, client, superuser):
        client.login(username="admin", password="adminpass123")
        response = client.get(reverse("admin:etl_monitor_pipelinealert_changelist"))
        assert response.status_code == 200


@pytest.mark.django_db
class TestAdminPortfolio:
    def test_portfoliosnapshot_changelist(self, client, superuser):
        client.login(username="admin", password="adminpass123")
        response = client.get(reverse("admin:portfolio_portfoliosnapshot_changelist"))
        assert response.status_code == 200

    def test_assetallocationtarget_changelist(self, client, superuser):
        client.login(username="admin", password="adminpass123")
        response = client.get(reverse("admin:portfolio_assetallocationtarget_changelist"))
        assert response.status_code == 200
