from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("wallets", "0003_align_transaction_schema")]

    operations = [
        migrations.AddField(model_name="withdrawal", name="queued_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AlterField(model_name="withdrawal", name="status", field=models.CharField(choices=[("scheduled", "Scheduled"), ("queued", "Queued"), ("processing", "Processing"), ("succeeded", "Succeeded"), ("failed", "Failed"), ("insufficient_funds", "Insufficient funds")], default="scheduled", max_length=24)),
        migrations.AddIndex(model_name="withdrawal", index=models.Index(fields=["status", "queued_at"], name="wallets_wit_status_e1d20a_idx")),
    ]
