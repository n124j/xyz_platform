"""
XYZ Platform — Client & Account Management Models

Represents the core entity hierarchy:
  Client → Account → Holding → Transaction
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal


class ClientTier(models.TextChoices):
    ULTRA_HIGH_NET_WORTH = "UHNW", "Ultra High Net Worth (>$30M)"
    HIGH_NET_WORTH = "HNW", "High Net Worth ($1M–$30M)"
    MASS_AFFLUENT = "MA", "Mass Affluent ($250K–$1M)"
    INSTITUTIONAL = "INST", "Institutional"


class AccountType(models.TextChoices):
    DISCRETIONARY = "DISC", "Discretionary Managed"
    ADVISORY = "ADV", "Advisory"
    CUSTODY = "CUST", "Custody Only"
    TRUST = "TRUST", "Trust Account"
    RETIREMENT = "RET", "Retirement (IRA/401k)"


class AssetClass(models.TextChoices):
    EQUITY = "EQ", "Equity"
    FIXED_INCOME = "FI", "Fixed Income"
    ALTERNATIVE = "ALT", "Alternative Investments"
    CASH = "CASH", "Cash & Equivalents"
    REAL_ESTATE = "RE", "Real Estate"
    COMMODITY = "COMM", "Commodities"


class Client(models.Model):
    """Private banking client profile."""
    client_id = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True)
    tier = models.CharField(max_length=10, choices=ClientTier.choices, default=ClientTier.HIGH_NET_WORTH)
    relationship_manager = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="clients"
    )
    onboarded_date = models.DateField()
    kyc_verified = models.BooleanField(default=False)
    kyc_verified_date = models.DateField(null=True, blank=True)
    risk_profile = models.CharField(
        max_length=20,
        choices=[
            ("CONSERVATIVE", "Conservative"),
            ("MODERATE", "Moderate"),
            ("AGGRESSIVE", "Aggressive"),
            ("VERY_AGGRESSIVE", "Very Aggressive"),
        ],
        default="MODERATE",
    )
    country = models.CharField(max_length=100, default="United States")
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["tier", "is_active"])]

    def __str__(self):
        return f"{self.client_id} — {self.name} ({self.get_tier_display()})"

    @property
    def total_aum(self):
        return sum(a.market_value for a in self.accounts.filter(is_active=True))


class Account(models.Model):
    """Investment account linked to a client."""
    account_number = models.CharField(max_length=20, unique=True, db_index=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="accounts")
    account_type = models.CharField(max_length=10, choices=AccountType.choices)
    inception_date = models.DateField()
    benchmark = models.CharField(max_length=50, default="S&P 500")
    base_currency = models.CharField(max_length=3, default="USD")
    market_value = models.DecimalField(
        max_digits=20, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    cash_balance = models.DecimalField(
        max_digits=20, decimal_places=2, default=Decimal("0.00")
    )
    ytd_return = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal("0.0000"))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-market_value"]

    def __str__(self):
        return f"{self.account_number} ({self.get_account_type_display()}) — {self.client.name}"


class Holding(models.Model):
    """A single position within an account."""
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="holdings")
    ticker = models.CharField(max_length=20, db_index=True)
    security_name = models.CharField(max_length=255)
    asset_class = models.CharField(max_length=10, choices=AssetClass.choices)
    quantity = models.DecimalField(max_digits=18, decimal_places=6)
    cost_basis = models.DecimalField(max_digits=20, decimal_places=4)
    market_price = models.DecimalField(max_digits=20, decimal_places=4)
    market_value = models.DecimalField(max_digits=20, decimal_places=2)
    unrealized_pnl = models.DecimalField(max_digits=20, decimal_places=2)
    weight = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal("0.0000"))
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("account", "ticker")]
        ordering = ["-market_value"]

    def __str__(self):
        return f"{self.ticker} — {self.account.account_number}"

    @property
    def unrealized_pnl_pct(self):
        cost = self.quantity * self.cost_basis
        if cost == 0:
            return Decimal("0.0000")
        return ((self.market_value - cost) / cost * 100).quantize(Decimal("0.0001"))


class Transaction(models.Model):
    """Trade and cash flow transaction record."""
    class TransactionType(models.TextChoices):
        BUY = "BUY", "Buy"
        SELL = "SELL", "Sell"
        DIVIDEND = "DIV", "Dividend"
        INTEREST = "INT", "Interest"
        FEE = "FEE", "Management Fee"
        TRANSFER_IN = "TFI", "Transfer In"
        TRANSFER_OUT = "TFO", "Transfer Out"
        DEPOSIT = "DEP", "Deposit"
        WITHDRAWAL = "WIT", "Withdrawal"

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=5, choices=TransactionType.choices)
    ticker = models.CharField(max_length=20, blank=True)
    security_name = models.CharField(max_length=255, blank=True)
    trade_date = models.DateField()
    settlement_date = models.DateField()
    quantity = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    price = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    gross_amount = models.DecimalField(max_digits=20, decimal_places=2)
    fees = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    net_amount = models.DecimalField(max_digits=20, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    reference_number = models.CharField(max_length=50, unique=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-trade_date", "-created_at"]
        indexes = [
            models.Index(fields=["account", "trade_date"]),
            models.Index(fields=["ticker", "trade_date"]),
        ]

    def __str__(self):
        return f"{self.reference_number} — {self.transaction_type} {self.ticker} @ {self.trade_date}"
