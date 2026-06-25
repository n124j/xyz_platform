from rest_framework import serializers

from .models import BenchmarkReturn, MarketData, PerformanceAttribution, RiskMetric


class MarketDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketData
        fields = "__all__"


class RiskMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskMetric
        fields = "__all__"


class BenchmarkReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = BenchmarkReturn
        fields = "__all__"


class PerformanceAttributionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerformanceAttribution
        fields = "__all__"
