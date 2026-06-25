from django.urls import path
from . import views

app_name = "analytics"

urlpatterns = [
    path("", views.AnalyticsDashboardView.as_view(), name="dashboard"),
    path("risk/", views.RiskMetricListView.as_view(), name="risk_metrics"),
    path("market-data/<str:ticker>/", views.MarketDataAPIView.as_view(), name="market_data_api"),
]
