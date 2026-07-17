from django.core.management.base import BaseCommand
from django.utils import timezone

from wallets.models import Withdrawal
from wallets.services.withdrawals import execute_withdrawal


class Command(BaseCommand):
    help = "Process scheduled withdrawals whose execution time has passed."

    def handle(self, *args, **options):
        withdrawals = Withdrawal.objects.filter(status=Withdrawal.Status.SCHEDULED, execute_at__lte=timezone.now()).order_by("execute_at")
        processed = 0
        for withdrawal in withdrawals:
            execute_withdrawal(withdrawal.uuid)
            processed += 1
        self.stdout.write(self.style.SUCCESS(f"Processed {processed} due withdrawal(s)."))
