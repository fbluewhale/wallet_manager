from rest_framework import serializers

from django.utils import timezone
from rest_framework import serializers

from wallets.models import Transaction, Wallet, Withdrawal


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ("uuid", "balance", "created_at", "updated_at")
        read_only_fields = ("uuid", "balance")


class DepositSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=1)


class WithdrawalCreateSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=1)
    execute_at = serializers.DateTimeField()

    def validate_execute_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("execute_at must be in the future.", code="invalid_execute_at")
        return value


class WithdrawalSerializer(serializers.ModelSerializer):
    wallet_uuid = serializers.UUIDField(source="wallet.uuid", read_only=True)

    class Meta:
        model = Withdrawal
        fields = (
            "uuid", "wallet_uuid", "amount", "execute_at", "status", "failure_code",
            "failure_message", "bank_reference", "created_at", "updated_at", "completed_at",
        )
        read_only_fields = fields


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ("id", "transaction_type", "amount", "balance_after", "withdrawal", "created_at")
        read_only_fields = fields
