from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("wallets", "0004_queued_withdrawals")]

    operations = [
        migrations.RemoveIndex(model_name="withdrawal", name="wallets_wit_status_e1d20a_idx"),
        migrations.AddIndex(model_name="withdrawal", index=models.Index(fields=["status", "queued_at"], name="wallets_wit_status_a52f37_idx")),
    ]
