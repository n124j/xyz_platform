"""XYZ Platform — Analytics Views (Risk & Market Data)."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView
from django.http import JsonResponse
from django.utils import timezone
from .models import MarketData, RiskMetric, BenchmarkReturn
from decimal import Decimal
import json


class AnalyticsDashboardView(LoginRequiredMixin, TemplateView):
    """Main analytics landing page with embedded Plotly Dash apps."""
    template_name = "analytics/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Risk & Market Analytics"
        portfolio_risk = RiskMetric.objects.filter(
            scope="PORTFOLIO", lookback_days=252
        ).order_by("-calculation_date").first()
        ctx["portfolio_risk"] = portfolio_risk
        if portfolio_risk:
            ctx["kpi_var95"] = f"{float(portfolio_risk.var_95_1d) * 100:.2f}%"
            ctx["kpi_sharpe"] = f"{float(portfolio_risk.sharpe_ratio):.2f}"
            ctx["kpi_maxdd"] = f"{float(portfolio_risk.max_drawdown) * 100:.2f}%"
            ctx["kpi_vol"] = f"{float(portfolio_risk.annualised_volatility) * 100:.2f}%"
        metrics = list(
            RiskMetric.objects.order_by("-calculation_date")
            .values(
                "scope", "reference_id", "calculation_date",
                "var_95_1d", "var_99_1d", "cvar_95_1d",
                "annualised_return", "annualised_volatility",
                "sharpe_ratio", "sortino_ratio", "max_drawdown",
                "beta", "alpha", "information_ratio", "tracking_error",
            )[:50]
        )
        for m in metrics:
            m["calculation_date"] = str(m["calculation_date"])
            for k, v in m.items():
                if isinstance(v, Decimal):
                    m[k] = float(v)
        ctx["risk_metrics_json"] = json.dumps(metrics)
        return ctx


class RiskMetricListView(LoginRequiredMixin, ListView):
    model = RiskMetric
    template_name = "analytics/risk_metrics.html"
    context_object_name = "risk_metrics"
    paginate_by = 30

    def get_queryset(self):
        qs = RiskMetric.objects.all()
        scope = self.request.GET.get("scope", "")
        if scope:
            qs = qs.filter(scope=scope)
        return qs


class MarketDataAPIView(LoginRequiredMixin, TemplateView):
    """JSON endpoint backing D3 price charts."""
    def get(self, request, ticker):
        days = int(request.GET.get("days", 90))
        since = timezone.now().date() - timezone.timedelta(days=days)
        records = MarketData.objects.filter(
            ticker=ticker.upper(), price_date__gte=since
        ).order_by("price_date").values("price_date", "close_price", "volume")
        data = [
            {"date": str(r["price_date"]), "close": float(r["close_price"]), "volume": r["volume"]}
            for r in records
        ]
        return JsonResponse({"ticker": ticker.upper(), "data": data})
