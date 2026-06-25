"""XYZ Platform — Account Management REST API ViewSets."""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Account, Client, Transaction
from .serializers import AccountSerializer, ClientSerializer, TransactionSerializer


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.filter(is_active=True).select_related("relationship_manager")
    serializer_class = ClientSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "client_id", "email"]
    ordering_fields = ["name", "onboarded_date"]

    @action(detail=True, methods=["get"])
    def aum_summary(self, request, pk=None):
        client = self.get_object()
        return Response({"client_id": client.client_id, "total_aum": float(client.total_aum)})


class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.filter(is_active=True).select_related("client")
    serializer_class = AccountSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["account_type", "base_currency", "client"]
    ordering_fields = ["market_value", "ytd_return"]


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Transaction.objects.all().select_related("account__client")
    serializer_class = TransactionSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["transaction_type", "ticker", "account"]
    ordering_fields = ["trade_date", "net_amount"]
