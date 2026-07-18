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
    """Reserve, call the bank without locks, then settle the reservation."""
    bank_client = bank_client or RequestsBankClient()

    # Claim one worker. This is a short transaction and never includes I/O.
    with transaction.atomic():
        try:
            withdrawal = Withdrawal.objects.select_for_update().select_related("wallet").get(uuid=withdrawal_uuid)
        except Withdrawal.DoesNotExist as exc:
            raise WalletServiceError("withdrawal_not_found", "Withdrawal does not exist.") from exc

        if withdrawal.status not in (Withdrawal.Status.SCHEDULED, Withdrawal.Status.QUEUED):
            return withdrawal
        if withdrawal.execute_at > timezone.now():
            raise WalletServiceError("withdrawal_not_due", "Withdrawal is not due yet.")

        withdrawal.transition(Withdrawal.Status.PROCESSING)
        withdrawal.save(update_fields=["status", "updated_at"])

    # Lock order is always withdrawal then wallet. Reserve before external I/O.
    with transaction.atomic():
        withdrawal = Withdrawal.objects.select_for_update().get(uuid=withdrawal_uuid)
        wallet = Wallet.objects.select_for_update().get(pk=withdrawal.wallet_id)
        if withdrawal.status != Withdrawal.Status.PROCESSING:
            return withdrawal
        if wallet.available_balance < withdrawal.amount:
            withdrawal.transition(Withdrawal.Status.INSUFFICIENT_FUNDS)
            withdrawal.complete(Withdrawal.Status.INSUFFICIENT_FUNDS, failure_code="insufficient_funds", failure_message="Wallet balance is insufficient.")
            withdrawal.save()
            return withdrawal
        wallet.reserved_balance += withdrawal.amount
        wallet.save(update_fields=["reserved_balance", "updated_at"])
        Transaction.objects.get_or_create(wallet=wallet, withdrawal=withdrawal, operation="reserve", defaults={"transaction_type": Transaction.Type.RESERVATION, "amount": withdrawal.amount, "balance_after": wallet.balance})
        withdrawal.transition(Withdrawal.Status.FUNDS_RESERVED)
        withdrawal.save(update_fields=["status", "updated_at"])

    result = bank_client.deposit(withdrawal.amount)

    # Settle after I/O in another short transaction.
    with transaction.atomic():
        withdrawal = Withdrawal.objects.select_for_update().get(uuid=withdrawal_uuid)
        wallet = Wallet.objects.select_for_update().get(pk=withdrawal.wallet_id)
        if withdrawal.status != Withdrawal.Status.FUNDS_RESERVED:
            return withdrawal
        if not result.succeeded:
            wallet.reserved_balance -= withdrawal.amount
            wallet.save(update_fields=["reserved_balance", "updated_at"])
            Transaction.objects.get_or_create(wallet=wallet, withdrawal=withdrawal, operation="release", defaults={"transaction_type": Transaction.Type.RESERVATION_RELEASE, "amount": withdrawal.amount, "balance_after": wallet.balance})
            withdrawal.complete(Withdrawal.Status.FAILED, failure_code=result.code or "bank_failed", failure_message=result.message)
            withdrawal.save()
            return withdrawal

        wallet.balance -= withdrawal.amount
        wallet.reserved_balance -= withdrawal.amount
        wallet.save(update_fields=["balance", "reserved_balance", "updated_at"])
        Transaction.objects.get_or_create(wallet=wallet, withdrawal=withdrawal, operation="complete", defaults={"transaction_type": Transaction.Type.WITHDRAWAL, "amount": withdrawal.amount, "balance_after": wallet.balance})
        withdrawal.complete(Withdrawal.Status.SUCCEEDED, bank_reference=result.reference)
        withdrawal.save()
        return withdrawal
