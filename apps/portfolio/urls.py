from django.urls import path
from . import views

app_name = "portfolio"

urlpatterns = [
    path("", views.PortfolioDashboardView.as_view(), name="dashboard"),
    path("api/snapshot/", views.PortfolioSnapshotAPIView.as_view(), name="snapshot_api"),
]
