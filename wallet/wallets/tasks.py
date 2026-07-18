import logging

from celery import shared_task

from wallets.services.withdrawals import execute_withdrawal

logger = logging.getLogger(__name__)


@shared_task(name="wallets.process_withdrawal")
def process_withdrawal(withdrawal_uuid):
    logger.info("withdrawal_task_started", extra={"withdrawal_id": str(withdrawal_uuid)})
    withdrawal = execute_withdrawal(withdrawal_uuid)
    logger.info("withdrawal_task_completed", extra={"withdrawal_id": str(withdrawal_uuid), "status": withdrawal.status})
    return withdrawal.status


@shared_task(name="wallets.dispatch_due_withdrawals")
def dispatch_due_withdrawals():
    from wallets.services.dispatch import dispatch_due_withdrawals as dispatch
    return dispatch()


@shared_task(name="wallets.publish_outbox")
def publish_outbox():
    from wallets.services.dispatch import publish_outbox_events
    return publish_outbox_events()
