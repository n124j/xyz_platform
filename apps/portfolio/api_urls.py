from django.urls import path

from .views import PortfolioSnapshotAPIView

urlpatterns = [
    path("snapshots/", PortfolioSnapshotAPIView.as_view(), name="portfolio-snapshots"),
]
