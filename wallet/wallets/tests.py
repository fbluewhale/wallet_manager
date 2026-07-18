from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from banking.client import BankResult
from wallets.models import Transaction, Wallet, Withdrawal
from wallets.services.deposits import deposit
from wallets.services.dispatch import dispatch_due_withdrawals, recover_stale_queued_withdrawals
from wallets.services.withdrawals import execute_withdrawal


class FakeBankClient:
    def __init__(self, result):
        self.result = result
        self.amounts = []

    def deposit(self, amount):
        self.amounts.append(amount)
        return self.result


class WalletApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.wallet = Wallet.objects.create()

    def test_creates_wallet(self):
        response = self.client.post("/wallets/", {}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["balance"], 0)

    def test_positive_deposit_updates_balance_and_history(self):
        response = self.client.post(f"/wallets/{self.wallet.uuid}/deposit", {"amount": 150}, format="json")
        self.assertEqual(response.status_code, 200)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, 150)
        transaction = Transaction.objects.get(wallet=self.wallet)
        self.assertEqual((transaction.transaction_type, transaction.amount, transaction.balance_after), ("deposit", 150, 150))

    def test_rejects_non_positive_deposit(self):
        response = self.client.post(f"/wallets/{self.wallet.uuid}/deposit", {"amount": 0}, format="json")
        self.assertEqual(response.status_code, 400)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, 0)

    def test_schedules_future_withdrawal_without_current_funds(self):
        execute_at = timezone.now() + timedelta(hours=1)
        response = self.client.post(f"/wallets/{self.wallet.uuid}/withdraw", {"amount": 500, "execute_at": execute_at.isoformat()}, format="json")
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["status"], Withdrawal.Status.SCHEDULED)

    def test_rejects_past_withdrawal(self):
        response = self.client.post(f"/wallets/{self.wallet.uuid}/withdraw", {"amount": 5, "execute_at": (timezone.now() - timedelta(seconds=1)).isoformat()}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "invalid_execute_at")


class WithdrawalExecutionTests(TestCase):
    def setUp(self):
        self.wallet = Wallet.objects.create(balance=100)

    def due_withdrawal(self, amount=40):
        return Withdrawal.objects.create(wallet=self.wallet, amount=amount, execute_at=timezone.now() - timedelta(seconds=1))

    def test_successful_execution_deducts_and_records_history(self):
        withdrawal = self.due_withdrawal()
        client = FakeBankClient(BankResult(True, reference="bank-1"))
        execute_withdrawal(withdrawal.uuid, client)
        self.wallet.refresh_from_db()
        withdrawal.refresh_from_db()
        self.assertEqual(self.wallet.balance, 60)
        self.assertEqual(withdrawal.status, Withdrawal.Status.SUCCEEDED)
        self.assertEqual(withdrawal.bank_reference, "bank-1")
        self.assertTrue(Transaction.objects.filter(withdrawal=withdrawal, transaction_type="withdrawal", balance_after=60).exists())
        self.assertEqual(client.amounts, [40])

    def test_insufficient_funds_does_not_call_bank_or_make_balance_negative(self):
        withdrawal = self.due_withdrawal(amount=101)
        client = FakeBankClient(BankResult(True))
        execute_withdrawal(withdrawal.uuid, client)
        self.wallet.refresh_from_db()
        withdrawal.refresh_from_db()
        self.assertEqual((self.wallet.balance, withdrawal.status, client.amounts), (100, Withdrawal.Status.INSUFFICIENT_FUNDS, []))
        self.assertFalse(Transaction.objects.filter(withdrawal=withdrawal).exists())

    def test_confirmed_bank_failure_keeps_balance(self):
        withdrawal = self.due_withdrawal()
        execute_withdrawal(withdrawal.uuid, FakeBankClient(BankResult(False, code="bank_rejected", message="failed")))
        self.wallet.refresh_from_db()
        withdrawal.refresh_from_db()
        self.assertEqual(self.wallet.balance, 100)
        self.assertEqual(withdrawal.status, Withdrawal.Status.FAILED)
        self.assertEqual(withdrawal.failure_code, "bank_rejected")

    def test_retrieves_withdrawal(self):
        withdrawal = self.due_withdrawal()
        response = APIClient().get(f"/wallets/withdrawals/{withdrawal.uuid}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["uuid"], str(withdrawal.uuid))

    def test_duplicate_task_execution_does_not_debit_twice(self):
        withdrawal = self.due_withdrawal()
        bank = FakeBankClient(BankResult(True))
        execute_withdrawal(withdrawal.uuid, bank)
        execute_withdrawal(withdrawal.uuid, bank)
        self.wallet.refresh_from_db()
        self.assertEqual((self.wallet.balance, bank.amounts), (60, [40]))
        self.assertEqual(Transaction.objects.filter(withdrawal=withdrawal, operation="complete").count(), 1)

    def test_competing_withdrawals_reserve_only_available_funds(self):
        first = self.due_withdrawal(amount=80)
        second = self.due_withdrawal(amount=80)
        bank = FakeBankClient(BankResult(True))
        execute_withdrawal(first.uuid, bank)
        execute_withdrawal(second.uuid, bank)
        self.wallet.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual((self.wallet.balance, self.wallet.reserved_balance), (20, 0))
        self.assertEqual(second.status, Withdrawal.Status.INSUFFICIENT_FUNDS)
        self.assertEqual(Transaction.objects.filter(transaction_type=Transaction.Type.RESERVATION).count(), 1)

    def test_bank_failure_releases_reservation(self):
        withdrawal = self.due_withdrawal()
        execute_withdrawal(withdrawal.uuid, FakeBankClient(BankResult(False, code="declined")))
        self.wallet.refresh_from_db()
        self.assertEqual((self.wallet.balance, self.wallet.reserved_balance), (100, 0))
        self.assertTrue(Transaction.objects.filter(withdrawal=withdrawal, operation="release").exists())


class WithdrawalDispatcherTests(TestCase):
    def setUp(self):
        self.wallet = Wallet.objects.create(balance=100)
        self.now = timezone.now()

    def withdrawal(self, *, execute_at, status=Withdrawal.Status.SCHEDULED, queued_at=None):
        return Withdrawal.objects.create(
            wallet=self.wallet, amount=10, execute_at=execute_at, status=status, queued_at=queued_at
        )

    def test_dispatcher_queues_due_withdrawals_once(self):
        due = self.withdrawal(execute_at=self.now - timedelta(seconds=1))
        enqueued = []
        with self.captureOnCommitCallbacks(execute=True):
            count = dispatch_due_withdrawals(now=self.now, enqueue=enqueued.append)
        due.refresh_from_db()
        self.assertEqual((count, due.status, enqueued), (1, Withdrawal.Status.QUEUED, [str(due.uuid)]))
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(dispatch_due_withdrawals(now=self.now, enqueue=enqueued.append), 0)
        self.assertEqual(enqueued, [str(due.uuid)])

    def test_dispatcher_ignores_future_and_completed_withdrawals(self):
        future = self.withdrawal(execute_at=self.now + timedelta(minutes=1))
        completed = self.withdrawal(execute_at=self.now - timedelta(seconds=1), status=Withdrawal.Status.SUCCEEDED)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(dispatch_due_withdrawals(now=self.now, enqueue=lambda _: None), 0)
        future.refresh_from_db()
        completed.refresh_from_db()
        self.assertEqual((future.status, completed.status), (Withdrawal.Status.SCHEDULED, Withdrawal.Status.SUCCEEDED))

    @patch("wallets.services.dispatch.settings.WITHDRAWAL_DISPATCH_BATCH_SIZE", 2)
    def test_dispatcher_respects_batch_size(self):
        for _ in range(3):
            self.withdrawal(execute_at=self.now - timedelta(seconds=1))
        enqueued = []
        with self.captureOnCommitCallbacks(execute=True):
            count = dispatch_due_withdrawals(now=self.now, enqueue=enqueued.append)
        self.assertEqual((count, len(enqueued)), (2, 2))
        self.assertEqual(Withdrawal.objects.filter(status=Withdrawal.Status.QUEUED).count(), 2)

    @patch("wallets.services.dispatch.settings.WITHDRAWAL_MAX_QUEUED_AGE_SECONDS", 60)
    def test_stale_queued_withdrawal_is_recovered(self):
        stale = self.withdrawal(
            execute_at=self.now - timedelta(minutes=2),
            status=Withdrawal.Status.QUEUED,
            queued_at=self.now - timedelta(minutes=2),
        )
        self.assertEqual(recover_stale_queued_withdrawals(now=self.now), 1)
        stale.refresh_from_db()
        self.assertEqual((stale.status, stale.queued_at), (Withdrawal.Status.SCHEDULED, None))

    @patch("wallets.tasks.execute_withdrawal")
    def test_celery_task_invokes_application_service(self, execute):
        from wallets.tasks import process_withdrawal

        withdrawal = self.withdrawal(execute_at=self.now - timedelta(seconds=1))
        execute.return_value = withdrawal
        self.assertEqual(process_withdrawal.run(str(withdrawal.uuid)), Withdrawal.Status.SCHEDULED)
        execute.assert_called_once_with(str(withdrawal.uuid))
