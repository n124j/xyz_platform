"""XYZ Platform — Account Management DRF Serializers."""
from rest_framework import serializers
from .models import Client, Account, Holding, Transaction


class HoldingSerializer(serializers.ModelSerializer):
    unrealized_pnl_pct = serializers.ReadOnlyField()

    class Meta:
        model = Holding
        fields = "__all__"


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = "__all__"


class AccountSerializer(serializers.ModelSerializer):
    holdings = HoldingSerializer(many=True, read_only=True)

    class Meta:
        model = Account
        fields = "__all__"


class ClientSerializer(serializers.ModelSerializer):
    total_aum = serializers.ReadOnlyField()
    accounts = AccountSerializer(many=True, read_only=True)

    class Meta:
        model = Client
        fields = "__all__"
