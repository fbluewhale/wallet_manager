"""Durable dispatcher: database state is authoritative, Celery is delivery."""

import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from django.db.models import Q
from wallets.models import Withdrawal

logger = logging.getLogger(__name__)


def recover_stale_queued_withdrawals(now=None):
    now = now or timezone.now()
    cutoff = now - timedelta(seconds=settings.WITHDRAWAL_MAX_QUEUED_AGE_SECONDS)
    recovered = Withdrawal.objects.filter(status=Withdrawal.Status.QUEUED, queued_at__lt=cutoff).update(
        status=Withdrawal.Status.SCHEDULED, queued_at=None
    )
    if recovered:
        logger.info("stale_queued_withdrawal_recovered", extra={"count": recovered})
    return recovered


def dispatch_due_withdrawals(now=None, enqueue=None):
    """Claim at most one batch and publish tasks after the claim commits."""
    now = now or timezone.now()
    logger.info("withdrawal_dispatcher_scan_started")
    recover_stale_queued_withdrawals(now)
    if enqueue is None:
        from wallets.tasks import process_withdrawal
        enqueue = process_withdrawal.delay

    with transaction.atomic():
        due = list(
            Withdrawal.objects.select_for_update(skip_locked=True)
            .filter(Q(status=Withdrawal.Status.SCHEDULED, execute_at__lte=now) | Q(status=Withdrawal.Status.RETRY_PENDING, next_retry_at__lte=now))
            .order_by("execute_at")[:settings.WITHDRAWAL_DISPATCH_BATCH_SIZE]
        )
        if due:
            logger.info("due_withdrawals_found", extra={"count": len(due)})
        for withdrawal in due:
            withdrawal.status = Withdrawal.Status.QUEUED
            withdrawal.queued_at = now
            withdrawal.save(update_fields=["status", "queued_at", "updated_at"])
            transaction.on_commit(lambda withdrawal_uuid=str(withdrawal.uuid): enqueue(withdrawal_uuid))
            logger.info("withdrawal_queued", extra={"withdrawal_id": str(withdrawal.uuid), "wallet_id": withdrawal.wallet_id})
    return len(due)
