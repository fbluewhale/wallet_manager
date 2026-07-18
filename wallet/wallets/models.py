import uuid

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
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)
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
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        INSUFFICIENT_FUNDS = "insufficient_funds", "Insufficient funds"

    uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="withdrawals")
    amount = models.BigIntegerField()
    execute_at = models.DateTimeField()
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.SCHEDULED)
    queued_at = models.DateTimeField(null=True, blank=True)
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
            self.Status.FUNDS_RESERVED: {self.Status.SUCCEEDED, self.Status.FAILED},
        }
        if target not in allowed.get(self.status, set()):
            raise ValueError(f"Invalid withdrawal transition: {self.status} -> {target}")
        self.status = target
