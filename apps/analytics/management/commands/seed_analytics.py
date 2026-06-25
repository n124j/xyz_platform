"""Generate realistic sample data for the Analytics dashboard."""
import numpy as np
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from apps.analytics.models import MarketData, RiskMetric, BenchmarkReturn


SECURITIES = {
    "AAPL":  {"name": "Apple Inc.",               "base": 195.0, "vol": 0.018},
    "MSFT":  {"name": "Microsoft Corp.",          "base": 420.0, "vol": 0.016},
    "JPM":   {"name": "JPMorgan Chase & Co.",     "base": 198.0, "vol": 0.014},
    "GS":    {"name": "Goldman Sachs Group Inc.", "base": 465.0, "vol": 0.017},
    "TLT":   {"name": "iShares 20+ Year Treasury","base": 92.0,  "vol": 0.008},
    "GLD":   {"name": "SPDR Gold Shares",         "base": 215.0, "vol": 0.009},
    "BRK.B": {"name": "Berkshire Hathaway B",     "base": 410.0, "vol": 0.012},
    "AMZN":  {"name": "Amazon.com Inc.",          "base": 185.0, "vol": 0.020},
}

BENCHMARKS = {
    "SP500":      {"name": "S&P 500 Total Return",    "base": 5400.0, "drift": 0.0003, "vol": 0.010},
    "MSCI_WORLD": {"name": "MSCI World Index",        "base": 3300.0, "drift": 0.0002, "vol": 0.009},
    "AGG":        {"name": "Bloomberg US Agg Bond",    "base": 100.0,  "drift": 0.0001, "vol": 0.004},
}


def _business_days(start, end):
    days = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


class Command(BaseCommand):
    help = "Seed MarketData, RiskMetric, and BenchmarkReturn with realistic sample data"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=180, help="Trading days to generate")
        parser.add_argument("--clear", action="store_true", help="Delete existing data first")

    def handle(self, *args, **options):
        n_days = options["days"]
        if options["clear"]:
            MarketData.objects.all().delete()
            RiskMetric.objects.all().delete()
            BenchmarkReturn.objects.all().delete()
            self.stdout.write("Cleared existing analytics data.")

        end_date = date.today()
        start_date = end_date - timedelta(days=int(n_days * 1.5))
        trading_days = _business_days(start_date, end_date)[-n_days:]

        np.random.seed(42)

        self._seed_market_data(trading_days)
        self._seed_benchmarks(trading_days)
        self._seed_risk_metrics(trading_days[-1])
        self.stdout.write(self.style.SUCCESS("Analytics sample data seeded successfully."))

    def _seed_market_data(self, trading_days):
        records = []
        for ticker, spec in SECURITIES.items():
            price = spec["base"]
            for day in trading_days:
                ret = np.random.normal(0.0003, spec["vol"])
                price *= (1 + ret)
                high = price * (1 + abs(np.random.normal(0, 0.005)))
                low = price * (1 - abs(np.random.normal(0, 0.005)))
                opn = price * (1 + np.random.normal(0, 0.003))
                vol = int(np.random.lognormal(17, 0.8))
                records.append(MarketData(
                    ticker=ticker,
                    security_name=spec["name"],
                    price_date=day,
                    open_price=Decimal(f"{opn:.4f}"),
                    high_price=Decimal(f"{high:.4f}"),
                    low_price=Decimal(f"{low:.4f}"),
                    close_price=Decimal(f"{price:.4f}"),
                    adjusted_close=Decimal(f"{price:.4f}"),
                    volume=vol,
                    currency="USD",
                    source="SEED",
                ))
        MarketData.objects.bulk_create(records, ignore_conflicts=True)
        self.stdout.write(f"  Created {len(records)} MarketData records")

    def _seed_benchmarks(self, trading_days):
        records = []
        for code, spec in BENCHMARKS.items():
            level = spec["base"]
            cum = 0.0
            for day in trading_days:
                daily_ret = np.random.normal(spec["drift"], spec["vol"])
                level *= (1 + daily_ret)
                cum += daily_ret
                records.append(BenchmarkReturn(
                    benchmark_code=code,
                    benchmark_name=spec["name"],
                    return_date=day,
                    daily_return=Decimal(f"{daily_ret:.6f}"),
                    cumulative_return=Decimal(f"{cum:.6f}"),
                    index_level=Decimal(f"{level:.4f}"),
                ))
        BenchmarkReturn.objects.bulk_create(records, ignore_conflicts=True)
        self.stdout.write(f"  Created {len(records)} BenchmarkReturn records")

    def _seed_risk_metrics(self, calc_date):
        records = []
        portfolio_metrics = {
            "reference_id": "PORTFOLIO",
            "scope": "PORTFOLIO",
            "var_95_1d": -0.0142, "var_99_1d": -0.0213, "cvar_95_1d": -0.0189,
            "annualised_return": 0.0845, "annualised_volatility": 0.1423,
            "sharpe_ratio": 0.594, "sortino_ratio": 0.812,
            "max_drawdown": -0.0876,
            "beta": 0.92, "alpha": 0.0031, "information_ratio": 0.45, "tracking_error": 0.0312,
        }
        records.append(RiskMetric(calculation_date=calc_date, lookback_days=252, **portfolio_metrics))

        account_data = [
            ("XYZ-1001", 0.0912, 0.1285, 0.71, -0.0654, 0.88, -0.0128, -0.0198),
            ("XYZ-1002", 0.0723, 0.1589, 0.46, -0.1102, 0.95, -0.0155, -0.0231),
            ("XYZ-1003", 0.1145, 0.1834, 0.62, -0.0943, 1.05, -0.0168, -0.0247),
            ("XYZ-1004", 0.0534, 0.0876, 0.61, -0.0432, 0.52, -0.0088, -0.0132),
            ("XYZ-1005", 0.0967, 0.1523, 0.63, -0.0789, 0.97, -0.0145, -0.0218),
        ]
        for acct, ann_ret, ann_vol, sharpe, max_dd, beta, var95, var99 in account_data:
            records.append(RiskMetric(
                scope="ACCOUNT", reference_id=acct, calculation_date=calc_date, lookback_days=252,
                var_95_1d=Decimal(f"{var95:.4f}"), var_99_1d=Decimal(f"{var99:.4f}"),
                cvar_95_1d=Decimal(f"{var95 * 1.3:.4f}"),
                annualised_return=Decimal(f"{ann_ret:.4f}"),
                annualised_volatility=Decimal(f"{ann_vol:.4f}"),
                sharpe_ratio=Decimal(f"{sharpe:.4f}"),
                sortino_ratio=Decimal(f"{sharpe * 1.15:.4f}"),
                max_drawdown=Decimal(f"{max_dd:.4f}"),
                beta=Decimal(f"{beta:.4f}"),
                alpha=Decimal(f"{np.random.uniform(-0.005, 0.008):.4f}"),
                information_ratio=Decimal(f"{np.random.uniform(0.1, 0.7):.4f}"),
                tracking_error=Decimal(f"{np.random.uniform(0.02, 0.06):.4f}"),
            ))

        for ticker in list(SECURITIES.keys()):
            records.append(RiskMetric(
                scope="SECURITY", reference_id=ticker, calculation_date=calc_date, lookback_days=252,
                var_95_1d=Decimal(f"{np.random.uniform(-0.025, -0.010):.4f}"),
                var_99_1d=Decimal(f"{np.random.uniform(-0.035, -0.018):.4f}"),
                annualised_return=Decimal(f"{np.random.uniform(-0.05, 0.20):.4f}"),
                annualised_volatility=Decimal(f"{np.random.uniform(0.10, 0.35):.4f}"),
                sharpe_ratio=Decimal(f"{np.random.uniform(-0.2, 1.2):.4f}"),
                max_drawdown=Decimal(f"{np.random.uniform(-0.25, -0.05):.4f}"),
                beta=Decimal(f"{np.random.uniform(0.5, 1.5):.4f}"),
            ))

        RiskMetric.objects.bulk_create(records, ignore_conflicts=True)
        self.stdout.write(f"  Created {len(records)} RiskMetric records")
