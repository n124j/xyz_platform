"""XYZ Platform — Client & Account Management Admin."""
from django.contrib import admin
from django.utils.html import format_html
from .models import Client, Account, Holding, Transaction


class AccountInline(admin.TabularInline):
    model = Account
    fields = ("account_number", "account_type", "market_value", "ytd_return", "is_active")
    readonly_fields = ("market_value", "ytd_return")
    extra = 0
    show_change_link = True


class HoldingInline(admin.TabularInline):
    model = Holding
    fields = ("ticker", "security_name", "asset_class", "quantity", "market_value", "unrealized_pnl", "weight")
    readonly_fields = ("market_value", "unrealized_pnl", "weight")
    extra = 0


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("client_id", "name", "tier", "kyc_verified", "total_aum_display", "relationship_manager", "is_active")
    list_filter = ("tier", "risk_profile", "kyc_verified", "is_active", "country")
    search_fields = ("client_id", "name", "email")
    readonly_fields = ("created_at", "updated_at")
    inlines = [AccountInline]
    fieldsets = (
        ("Identity", {"fields": ("client_id", "name", "email", "phone", "country")}),
        ("Classification", {"fields": ("tier", "risk_profile", "relationship_manager")}),
        ("KYC", {"fields": ("kyc_verified", "kyc_verified_date", "onboarded_date")}),
        ("Status", {"fields": ("is_active", "notes")}),
        ("Audit", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Total AUM")
    def total_aum_display(self, obj):
        aum = obj.total_aum
        return format_html('<strong>${}</strong>', f"{aum:,.0f}")


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("account_number", "client", "account_type", "market_value", "ytd_return", "base_currency", "is_active")
    list_filter = ("account_type", "base_currency", "is_active")
    search_fields = ("account_number", "client__name", "client__client_id")
    readonly_fields = ("created_at", "updated_at")
    inlines = [HoldingInline]


@admin.register(Holding)
class HoldingAdmin(admin.ModelAdmin):
    list_display = ("ticker", "security_name", "asset_class", "account", "quantity", "market_value", "unrealized_pnl")
    list_filter = ("asset_class",)
    search_fields = ("ticker", "security_name", "account__account_number")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("reference_number", "account", "transaction_type", "ticker", "trade_date", "net_amount", "currency")
    list_filter = ("transaction_type", "currency", "trade_date")
    search_fields = ("reference_number", "ticker", "account__account_number")
    date_hierarchy = "trade_date"
    readonly_fields = ("created_at",)
