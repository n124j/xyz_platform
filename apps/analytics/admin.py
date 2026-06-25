from django.contrib import admin

from .models import BenchmarkReturn, MarketData, PerformanceAttribution, RiskMetric


@admin.register(MarketData)
class MarketDataAdmin(admin.ModelAdmin):
    list_display = (
        "ticker",
        "security_name",
        "price_date",
        "close_price",
        "volume",
        "source",
    )
    list_filter = ("currency", "source")
    search_fields = ("ticker", "security_name")
    date_hierarchy = "price_date"


@admin.register(RiskMetric)
class RiskMetricAdmin(admin.ModelAdmin):
    list_display = (
        "scope",
        "reference_id",
        "calculation_date",
        "var_95_1d",
        "sharpe_ratio",
        "max_drawdown",
    )
    list_filter = ("scope",)
    search_fields = ("reference_id",)
    date_hierarchy = "calculation_date"


@admin.register(BenchmarkReturn)
class BenchmarkReturnAdmin(admin.ModelAdmin):
    list_display = (
        "benchmark_code",
        "benchmark_name",
        "return_date",
        "daily_return",
        "index_level",
    )
    list_filter = ("benchmark_code",)
    date_hierarchy = "return_date"


@admin.register(PerformanceAttribution)
class PerformanceAttributionAdmin(admin.ModelAdmin):
    list_display = (
        "account_number",
        "period_start",
        "period_end",
        "asset_class",
        "total_effect",
    )
    list_filter = ("asset_class",)
    search_fields = ("account_number",)
