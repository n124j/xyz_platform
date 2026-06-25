"""
XYZ Platform — Portfolio Dashboard Models

Stores aggregated portfolio-level statistics and snapshots
used by Plotly Dash and D3.js visualisations.
"""
from django.db import models
from decimal import Decimal


class PortfolioSnapshot(models.Model):
    """
    Daily AUM and performance snapshot — persisted by the
    portfolio_etl_dag Airflow pipeline after each market close.
    """
    snapshot_date = models.DateField(db_index=True)
    total_aum = models.DecimalField(max_digits=22, decimal_places=2)
    equity_value = models.DecimalField(max_digits=22, decimal_places=2, default=Decimal("0"))
    fixed_income_value = models.DecimalField(max_digits=22, decimal_places=2, default=Decimal("0"))
    alternatives_value = models.DecimalField(max_digits=22, decimal_places=2, default=Decimal("0"))
    cash_value = models.DecimalField(max_digits=22, decimal_places=2, default=Decimal("0"))
    daily_pnl = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    daily_return_pct = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal("0"))
    ytd_return_pct = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal("0"))
    client_count = models.IntegerField(default=0)
    account_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("snapshot_date",)]
        ordering = ["-snapshot_date"]

    def __str__(self):
        return f"Portfolio Snapshot {self.snapshot_date} — AUM ${self.total_aum:,.0f}"

    @property
    def equity_weight(self):
        if not self.total_aum:
            return 0
        return float(self.equity_value / self.total_aum * 100)

    @property
    def fixed_income_weight(self):
        if not self.total_aum:
            return 0
        return float(self.fixed_income_value / self.total_aum * 100)


class AssetAllocationTarget(models.Model):
    """Strategic asset allocation targets per risk profile."""
    risk_profile = models.CharField(max_length=20, unique=True)
    equity_target_pct = models.DecimalField(max_digits=5, decimal_places=2)
    fixed_income_target_pct = models.DecimalField(max_digits=5, decimal_places=2)
    alternatives_target_pct = models.DecimalField(max_digits=5, decimal_places=2)
    cash_target_pct = models.DecimalField(max_digits=5, decimal_places=2)
    rebalance_threshold_pct = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("5.00"))
    effective_date = models.DateField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["risk_profile"]

    def __str__(self):
        return f"SAA Target — {self.risk_profile}"
