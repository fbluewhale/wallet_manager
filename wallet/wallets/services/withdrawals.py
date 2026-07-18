from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from banking.client import RequestsBankClient
from wallets.models import BankTransferAttempt, Transaction, Wallet, Withdrawal
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

        if withdrawal.status not in (Withdrawal.Status.SCHEDULED, Withdrawal.Status.QUEUED, Withdrawal.Status.RETRY_PENDING):
            return withdrawal
        if withdrawal.execute_at > timezone.now():
            raise WalletServiceError("withdrawal_not_due", "Withdrawal is not due yet.")

        if withdrawal.status == Withdrawal.Status.RETRY_PENDING:
            withdrawal.transition(Withdrawal.Status.FUNDS_RESERVED)
        else:
            withdrawal.transition(Withdrawal.Status.PROCESSING)
        withdrawal.save(update_fields=["status", "updated_at"])

    # Lock order is always withdrawal then wallet. Reserve before external I/O.
    with transaction.atomic():
        withdrawal = Withdrawal.objects.select_for_update().get(uuid=withdrawal_uuid)
        wallet = Wallet.objects.select_for_update().get(pk=withdrawal.wallet_id)
        if withdrawal.status == Withdrawal.Status.FUNDS_RESERVED:
            pass
        elif withdrawal.status != Withdrawal.Status.PROCESSING:
            return withdrawal
        if withdrawal.status == Withdrawal.Status.PROCESSING and wallet.available_balance < withdrawal.amount:
            withdrawal.transition(Withdrawal.Status.INSUFFICIENT_FUNDS)
            withdrawal.complete(Withdrawal.Status.INSUFFICIENT_FUNDS, failure_code="insufficient_funds", failure_message="Wallet balance is insufficient.")
            withdrawal.save()
            return withdrawal
        if withdrawal.status == Withdrawal.Status.PROCESSING:
            wallet.reserved_balance += withdrawal.amount
            wallet.save(update_fields=["reserved_balance", "updated_at"])
            Transaction.objects.get_or_create(wallet=wallet, withdrawal=withdrawal, operation="reserve", defaults={"transaction_type": Transaction.Type.RESERVATION, "amount": withdrawal.amount, "balance_after": wallet.balance})
            withdrawal.transition(Withdrawal.Status.FUNDS_RESERVED)
        withdrawal.attempt_count += 1
        withdrawal.last_attempted_at = timezone.now()
        BankTransferAttempt.objects.create(withdrawal=withdrawal, attempt_number=withdrawal.attempt_count, idempotency_key=withdrawal.bank_idempotency_key, outcome="started")
        withdrawal.save()

    result = bank_client.deposit(withdrawal.amount)

    # Settle after I/O in another short transaction.
    with transaction.atomic():
        withdrawal = Withdrawal.objects.select_for_update().get(uuid=withdrawal_uuid)
        wallet = Wallet.objects.select_for_update().get(pk=withdrawal.wallet_id)
        if withdrawal.status != Withdrawal.Status.FUNDS_RESERVED:
            return withdrawal
        attempt = withdrawal.bank_attempts.get(attempt_number=withdrawal.attempt_count)
        attempt.outcome = result.outcome
        attempt.failure_code = result.code
        attempt.completed_at = timezone.now()
        attempt.save()
        if result.outcome in ("retryable_failure", "ambiguous_failure"):
            if withdrawal.attempt_count >= settings.BANK_MAX_RETRIES:
                withdrawal.transition(Withdrawal.Status.RECONCILIATION_REQUIRED)
                withdrawal.last_failure_code = result.code
                withdrawal.last_failure_message = result.message
                withdrawal.save()
                return withdrawal
            delay = min(settings.BANK_RETRY_MAX_SECONDS, settings.BANK_RETRY_BASE_SECONDS * (2 ** (withdrawal.attempt_count - 1)))
            withdrawal.transition(Withdrawal.Status.RETRY_PENDING)
            withdrawal.next_retry_at = timezone.now() + timedelta(seconds=delay)
            withdrawal.last_failure_code = result.code
            withdrawal.last_failure_message = result.message
            withdrawal.save()
            return withdrawal
        if result.outcome != "success":
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
