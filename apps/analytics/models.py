"""
XYZ Platform — Market Data & Risk Analytics Models

Stores market prices, risk metrics (VaR, volatility, beta), and
benchmark performance series used across Plotly Dash dashboards.
"""

from django.db import models


class MarketData(models.Model):
    """Daily OHLCV price record for a security."""

    ticker = models.CharField(max_length=20, db_index=True)
    security_name = models.CharField(max_length=255)
    price_date = models.DateField(db_index=True)
    open_price = models.DecimalField(max_digits=20, decimal_places=4)
    high_price = models.DecimalField(max_digits=20, decimal_places=4)
    low_price = models.DecimalField(max_digits=20, decimal_places=4)
    close_price = models.DecimalField(max_digits=20, decimal_places=4)
    adjusted_close = models.DecimalField(max_digits=20, decimal_places=4)
    volume = models.BigIntegerField(default=0)
    currency = models.CharField(max_length=3, default="USD")
    source = models.CharField(max_length=50, default="INTERNAL")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("ticker", "price_date")]
        ordering = ["-price_date"]
        indexes = [models.Index(fields=["ticker", "-price_date"])]

    def __str__(self):
        return f"{self.ticker} @ {self.price_date} — ${self.close_price}"


class RiskMetric(models.Model):
    """Computed risk statistics for an account or benchmark."""

    class MetricScope(models.TextChoices):
        ACCOUNT = "ACCOUNT", "Account"
        PORTFOLIO = "PORTFOLIO", "Portfolio"
        SECURITY = "SECURITY", "Security"

    scope = models.CharField(max_length=15, choices=MetricScope.choices)
    reference_id = models.CharField(max_length=50, help_text="Account number, ticker, or portfolio ID")
    calculation_date = models.DateField(db_index=True)

    # Value at Risk
    var_95_1d = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="1-day 95% VaR as % of NAV",
    )
    var_99_1d = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="1-day 99% VaR as % of NAV",
    )
    cvar_95_1d = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Conditional VaR (Expected Shortfall)",
    )

    # Return metrics
    annualised_return = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    annualised_volatility = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    sharpe_ratio = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    sortino_ratio = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    max_drawdown = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    # Market risk
    beta = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    alpha = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    information_ratio = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    tracking_error = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)

    lookback_days = models.IntegerField(default=252, help_text="Rolling window in trading days")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("scope", "reference_id", "calculation_date", "lookback_days")]
        ordering = ["-calculation_date"]

    def __str__(self):
        return f"{self.scope} {self.reference_id} risk @ {self.calculation_date}"


class BenchmarkReturn(models.Model):
    """Daily total-return index for standard benchmarks."""

    benchmark_code = models.CharField(max_length=20, db_index=True)
    benchmark_name = models.CharField(max_length=100)
    return_date = models.DateField()
    daily_return = models.DecimalField(max_digits=10, decimal_places=6)
    cumulative_return = models.DecimalField(max_digits=10, decimal_places=6)
    index_level = models.DecimalField(max_digits=15, decimal_places=4)

    class Meta:
        unique_together = [("benchmark_code", "return_date")]
        ordering = ["-return_date"]

    def __str__(self):
        return f"{self.benchmark_code} @ {self.return_date}"


class PerformanceAttribution(models.Model):
    """Brinson-Hood-Beebower performance attribution record."""

    account_number = models.CharField(max_length=20, db_index=True)
    period_start = models.DateField()
    period_end = models.DateField()
    asset_class = models.CharField(max_length=10)
    allocation_effect = models.DecimalField(max_digits=10, decimal_places=6)
    selection_effect = models.DecimalField(max_digits=10, decimal_places=6)
    interaction_effect = models.DecimalField(max_digits=10, decimal_places=6)
    total_effect = models.DecimalField(max_digits=10, decimal_places=6)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-period_end"]

    def __str__(self):
        return f"{self.account_number} attribution {self.period_start}–{self.period_end}"
