"""XYZ Platform — Analytics REST API."""
from rest_framework import viewsets, filters
from .models import MarketData, RiskMetric
from .serializers import MarketDataSerializer, RiskMetricSerializer


class MarketDataViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MarketData.objects.all()
    serializer_class = MarketDataSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["ticker", "security_name"]
    ordering_fields = ["price_date", "close_price"]
    filterset_fields = ["ticker", "currency"]


class RiskMetricViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RiskMetric.objects.all()
    serializer_class = RiskMetricSerializer
    filter_backends = [filters.OrderingFilter]
    filterset_fields = ["scope", "reference_id"]
    ordering_fields = ["calculation_date"]
