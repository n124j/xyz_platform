from rest_framework.routers import DefaultRouter

from .api_views import MarketDataViewSet, RiskMetricViewSet

router = DefaultRouter()
router.register("market-data", MarketDataViewSet, basename="market-data")
router.register("risk-metrics", RiskMetricViewSet, basename="risk-metric")

urlpatterns = router.urls
