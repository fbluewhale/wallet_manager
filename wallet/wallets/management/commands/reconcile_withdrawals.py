from django.core.management.base import BaseCommand

from wallets.models import Withdrawal


class Command(BaseCommand):
    help = "List reconciliation-required withdrawals. The supplied bank has no status lookup API."

    def handle(self, *args, **options):
        unresolved = Withdrawal.objects.filter(status=Withdrawal.Status.RECONCILIATION_REQUIRED).select_related("wallet").order_by("created_at")
        for withdrawal in unresolved:
            self.stdout.write(f"{withdrawal.uuid} wallet={withdrawal.wallet.uuid} amount={withdrawal.amount} attempts={withdrawal.attempt_count} key={withdrawal.bank_idempotency_key}")
        self.stdout.write(self.style.WARNING(f"Unresolved withdrawals: {unresolved.count()}"))
