from django.db import transaction

from wallets.models import Transaction, Wallet
from wallets.services.exceptions import WalletServiceError


def deposit(wallet_uuid, amount):
    if amount <= 0:
        raise WalletServiceError("invalid_amount", "amount must be positive.")
    with transaction.atomic():
        try:
            wallet = Wallet.objects.select_for_update().get(uuid=wallet_uuid)
        except Wallet.DoesNotExist as exc:
            raise WalletServiceError("wallet_not_found", "Wallet does not exist.") from exc
        wallet.balance += amount
        wallet.save(update_fields=["balance", "updated_at"])
        Transaction.objects.create(
            wallet=wallet,
            transaction_type=Transaction.Type.DEPOSIT,
            amount=amount,
            balance_after=wallet.balance,
        )
    return wallet
