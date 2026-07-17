import uuid

from django.db import migrations, models
from django.utils import timezone


def populate_transaction_timestamps(apps, schema_editor):
    Transaction = apps.get_model("wallets", "Transaction")
    Transaction.objects.filter(created_at__isnull=True).update(created_at=timezone.now())


class Migration(migrations.Migration):
    dependencies = [("wallets", "0002_wallet_withdrawal_transaction_history")]

    operations = [
        migrations.RunPython(populate_transaction_timestamps, migrations.RunPython.noop),
        migrations.AlterField(model_name="transaction", name="balance_after", field=models.BigIntegerField()),
        migrations.AlterField(model_name="transaction", name="created_at", field=models.DateTimeField(auto_now_add=True)),
        migrations.AlterField(model_name="transaction", name="transaction_type", field=models.CharField(choices=[("deposit", "Deposit"), ("withdrawal", "Withdrawal")], max_length=16)),
        migrations.AlterField(model_name="withdrawal", name="uuid", field=models.UUIDField(default=uuid.uuid4, unique=True)),
    ]
