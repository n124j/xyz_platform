from django.contrib import admin

from .models import AssetAllocationTarget, PortfolioSnapshot


@admin.register(PortfolioSnapshot)
class PortfolioSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "snapshot_date",
        "total_aum",
        "daily_return_pct",
        "ytd_return_pct",
        "client_count",
    )
    date_hierarchy = "snapshot_date"
    readonly_fields = ("created_at",)


@admin.register(AssetAllocationTarget)
class AssetAllocationTargetAdmin(admin.ModelAdmin):
    list_display = (
        "risk_profile",
        "equity_target_pct",
        "fixed_income_target_pct",
        "alternatives_target_pct",
        "cash_target_pct",
        "effective_date",
    )
