"""XYZ Platform — Portfolio Dashboard Views."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import JsonResponse
from apps.accounts.models import Client, Account
from .models import PortfolioSnapshot


class PortfolioDashboardView(LoginRequiredMixin, TemplateView):
    """
    Main landing page — embeds the Plotly Dash portfolio dashboard
    and summary KPI cards (AUM, daily P&L, YTD return, client count).
    """
    template_name = "portfolio/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        latest = PortfolioSnapshot.objects.order_by("-snapshot_date").first()
        ctx["snapshot"] = latest
        ctx["client_count"] = Client.objects.filter(is_active=True).count()
        ctx["account_count"] = Account.objects.filter(is_active=True).count()
        ctx["page_title"] = "Portfolio Overview"
        return ctx


class PortfolioSnapshotAPIView(LoginRequiredMixin, TemplateView):
    """JSON series for D3.js AUM trend chart."""
    def get(self, request):
        days = int(request.GET.get("days", 90))
        snapshots = PortfolioSnapshot.objects.order_by("-snapshot_date")[:days]
        data = [
            {
                "date": str(s.snapshot_date),
                "aum": float(s.total_aum),
                "daily_return": float(s.daily_return_pct),
                "ytd_return": float(s.ytd_return_pct),
            }
            for s in reversed(list(snapshots))
        ]
        return JsonResponse({"series": data})
