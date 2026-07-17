from django.db import transaction
from django.utils import timezone

from banking.client import RequestsBankClient
from wallets.models import Transaction, Wallet, Withdrawal
from wallets.services.exceptions import WalletServiceError


def schedule_withdrawal(wallet_uuid, amount, execute_at):
    if amount <= 0:
        raise WalletServiceError("invalid_amount", "amount must be positive.")
    if execute_at <= timezone.now():
        raise WalletServiceError("invalid_execute_at", "execute_at must be in the future.")
    try:
        wallet = Wallet.objects.get(uuid=wallet_uuid)
    except Wallet.DoesNotExist as exc:
        raise WalletServiceError("wallet_not_found", "Wallet does not exist.") from exc
    return Withdrawal.objects.create(wallet=wallet, amount=amount, execute_at=execute_at)


def execute_withdrawal(withdrawal_uuid, bank_client=None):
    """Execute one due withdrawal. Safe for the milestone's single-worker model."""
    bank_client = bank_client or RequestsBankClient()
    with transaction.atomic():
        try:
            withdrawal = Withdrawal.objects.select_for_update().select_related("wallet").get(uuid=withdrawal_uuid)
        except Withdrawal.DoesNotExist as exc:
            raise WalletServiceError("withdrawal_not_found", "Withdrawal does not exist.") from exc

        if withdrawal.status != Withdrawal.Status.SCHEDULED:
            return withdrawal
        if withdrawal.execute_at > timezone.now():
            raise WalletServiceError("withdrawal_not_due", "Withdrawal is not due yet.")

        wallet = Wallet.objects.select_for_update().get(pk=withdrawal.wallet_id)
        if wallet.balance < withdrawal.amount:
            withdrawal.complete(Withdrawal.Status.INSUFFICIENT_FUNDS, failure_code="insufficient_funds", failure_message="Wallet balance is insufficient.")
            withdrawal.save()
            return withdrawal

        withdrawal.status = Withdrawal.Status.PROCESSING
        withdrawal.save(update_fields=["status", "updated_at"])
        result = bank_client.deposit(withdrawal.amount)
        if not result.succeeded:
            withdrawal.complete(Withdrawal.Status.FAILED, failure_code=result.code or "bank_failed", failure_message=result.message)
            withdrawal.save()
            return withdrawal

        wallet.balance -= withdrawal.amount
        wallet.save(update_fields=["balance", "updated_at"])
        Transaction.objects.create(wallet=wallet, transaction_type=Transaction.Type.WITHDRAWAL, amount=withdrawal.amount, balance_after=wallet.balance, withdrawal=withdrawal)
        withdrawal.complete(Withdrawal.Status.SUCCEEDED, bank_reference=result.reference)
        withdrawal.save()
        return withdrawal
