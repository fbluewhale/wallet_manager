from rest_framework import status
from rest_framework.generics import CreateAPIView, RetrieveAPIView, RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from wallets.models import Wallet, Withdrawal
from wallets.serializers import DepositSerializer, WalletSerializer, WithdrawalCreateSerializer, WithdrawalSerializer
from wallets.services.deposits import deposit
from wallets.services.exceptions import WalletServiceError
from wallets.services.withdrawals import schedule_withdrawal


def error_response(error):
    return Response({"error": {"code": error.code, "message": error.message, "details": {}}}, status=status.HTTP_400_BAD_REQUEST)


class CreateWalletView(CreateAPIView):
    serializer_class = WalletSerializer


class RetrieveWalletView(RetrieveAPIView):
    serializer_class = WalletSerializer
    queryset = Wallet.objects.all()
    lookup_field = "uuid"


class CreateDepositView(APIView):
    def post(self, request, uuid, *args, **kwargs):
        serializer = DepositSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            wallet = deposit(uuid, serializer.validated_data["amount"])
        except WalletServiceError as exc:
            return error_response(exc)
        return Response(WalletSerializer(wallet).data, status=status.HTTP_200_OK)


class ScheduleWithdrawView(APIView):
    def post(self, request, uuid, *args, **kwargs):
        serializer = WithdrawalCreateSerializer(data=request.data)
        if not serializer.is_valid():
            if "execute_at" in serializer.errors:
                return Response({"error": {"code": "invalid_execute_at", "message": "execute_at must be in the future.", "details": serializer.errors}}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"error": {"code": "invalid_amount", "message": "amount must be positive.", "details": serializer.errors}}, status=status.HTTP_400_BAD_REQUEST)
        try:
            withdrawal = schedule_withdrawal(uuid, **serializer.validated_data)
        except WalletServiceError as exc:
            return error_response(exc)
        return Response(WithdrawalSerializer(withdrawal).data, status=status.HTTP_202_ACCEPTED)


class RetrieveWithdrawalView(RetrieveAPIView):
    serializer_class = WithdrawalSerializer
    queryset = Withdrawal.objects.select_related("wallet")
    lookup_field = "uuid"
