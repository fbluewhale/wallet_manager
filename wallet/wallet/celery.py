import os
from datetime import timedelta

from celery import Celery
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wallet.settings")

app = Celery("wallet")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.conf.beat_schedule = {
    "dispatch-due-withdrawals": {
        "task": "wallets.dispatch_due_withdrawals",
        "schedule": timedelta(seconds=settings.DISPATCHER_INTERVAL_SECONDS),
    }
}
