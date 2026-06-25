"""XYZ Platform — Client & Account Management Views."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.views.generic import DetailView, ListView

from .models import Account, Client, Transaction


class ClientListView(LoginRequiredMixin, ListView):
    model = Client
    template_name = "accounts/client_list.html"
    context_object_name = "clients"
    paginate_by = 25

    def get_queryset(self):
        qs = Client.objects.filter(is_active=True).select_related("relationship_manager")
        q = self.request.GET.get("q", "")
        tier = self.request.GET.get("tier", "")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(client_id__icontains=q) | Q(email__icontains=q))
        if tier:
            qs = qs.filter(tier=tier)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tiers"] = Client.ClientTier.choices if hasattr(Client, "ClientTier") else []
        from .models import ClientTier

        ctx["tiers"] = ClientTier.choices
        ctx["total_aum"] = (
            Client.objects.filter(is_active=True).aggregate(total=Sum("accounts__market_value"))["total"] or 0
        )
        return ctx


class ClientDetailView(LoginRequiredMixin, DetailView):
    model = Client
    template_name = "accounts/client_detail.html"
    context_object_name = "client"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        client = self.get_object()
        ctx["accounts"] = client.accounts.filter(is_active=True)
        ctx["recent_transactions"] = Transaction.objects.filter(account__client=client).order_by("-trade_date")[:20]
        return ctx


class AccountDetailView(LoginRequiredMixin, DetailView):
    model = Account
    template_name = "accounts/account_detail.html"
    context_object_name = "account"
    slug_field = "account_number"
    slug_url_kwarg = "account_number"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        account = self.get_object()
        ctx["holdings"] = account.holdings.all().order_by("-market_value")
        ctx["transactions"] = account.transactions.order_by("-trade_date")[:50]
        return ctx
