import uuid as uuid_lib

from django.db import models
from django.db.models import Q
from django.utils import timezone


class Transaction(models.Model):
    class Type(models.TextChoices):
        DEPOSIT = "deposit", "Deposit"
        RESERVATION = "reservation", "Reservation"
        RESERVATION_RELEASE = "reservation_release", "Reservation release"
        WITHDRAWAL = "withdrawal", "Withdrawal"

    wallet = models.ForeignKey("Wallet", on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=24, choices=Type.choices)
    amount = models.BigIntegerField()
    balance_after = models.BigIntegerField()
    withdrawal = models.ForeignKey(
        "Withdrawal", on_delete=models.SET_NULL, null=True, blank=True, related_name="transaction"
    )
    operation = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(check=Q(amount__gt=0), name="transaction_amount_positive"),
            models.UniqueConstraint(fields=["withdrawal", "operation"], name="unique_withdrawal_ledger_operation"),
        ]


class Wallet(models.Model):
    uuid = models.UUIDField(default=uuid_lib.uuid4, unique=True)
    balance = models.BigIntegerField(default=0)
    reserved_balance = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(check=Q(balance__gte=0), name="wallet_balance_non_negative"),
            models.CheckConstraint(check=Q(reserved_balance__gte=0), name="wallet_reserved_non_negative"),
            models.CheckConstraint(check=Q(reserved_balance__lte=models.F("balance")), name="wallet_reserved_within_balance"),
        ]

    @property
    def available_balance(self):
        return self.balance - self.reserved_balance


class Withdrawal(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        FUNDS_RESERVED = "funds_reserved", "Funds reserved"
        RETRY_PENDING = "retry_pending", "Retry pending"
        RECONCILIATION_REQUIRED = "reconciliation_required", "Reconciliation required"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        INSUFFICIENT_FUNDS = "insufficient_funds", "Insufficient funds"

    uuid = models.UUIDField(default=uuid_lib.uuid4, unique=True)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="withdrawals")
    amount = models.BigIntegerField()
    execute_at = models.DateTimeField()
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.SCHEDULED)
    queued_at = models.DateTimeField(null=True, blank=True)
    bank_idempotency_key = models.UUIDField(default=uuid_lib.uuid4, unique=True)
    attempt_count = models.PositiveIntegerField(default=0)
    last_attempted_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    last_failure_code = models.CharField(max_length=64, blank=True)
    last_failure_message = models.TextField(blank=True)
    failure_code = models.CharField(max_length=64, blank=True)
    failure_message = models.TextField(blank=True)
    bank_reference = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(check=Q(amount__gt=0), name="withdrawal_amount_positive")]
        indexes = [models.Index(fields=["status", "execute_at"]), models.Index(fields=["status", "queued_at"])]

    def complete(self, status, *, failure_code="", failure_message="", bank_reference=""):
        self.status = status
        self.failure_code = failure_code
        self.failure_message = failure_message
        self.bank_reference = bank_reference
        self.completed_at = timezone.now()

    def transition(self, target):
        allowed = {
            self.Status.SCHEDULED: {self.Status.QUEUED, self.Status.PROCESSING},
            self.Status.QUEUED: {self.Status.PROCESSING, self.Status.SCHEDULED},
            self.Status.PROCESSING: {self.Status.FUNDS_RESERVED, self.Status.INSUFFICIENT_FUNDS},
            self.Status.FUNDS_RESERVED: {self.Status.SUCCEEDED, self.Status.FAILED, self.Status.RETRY_PENDING, self.Status.RECONCILIATION_REQUIRED},
            self.Status.RETRY_PENDING: {self.Status.FUNDS_RESERVED, self.Status.RECONCILIATION_REQUIRED},
        }
        if target not in allowed.get(self.status, set()):
            raise ValueError(f"Invalid withdrawal transition: {self.status} -> {target}")
        self.status = target


class BankTransferAttempt(models.Model):
    withdrawal = models.ForeignKey(Withdrawal, on_delete=models.CASCADE, related_name="bank_attempts")
    attempt_number = models.PositiveIntegerField()
    idempotency_key = models.UUIDField()
    outcome = models.CharField(max_length=32)
    failure_code = models.CharField(max_length=64, blank=True)
    bank_reference = models.CharField(max_length=128, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["withdrawal", "attempt_number"], name="unique_bank_attempt_number")]
