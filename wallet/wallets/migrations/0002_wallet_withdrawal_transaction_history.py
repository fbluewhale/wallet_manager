from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("wallets", "0001_initial")]

    operations = [
        migrations.AddField(model_name="wallet", name="created_at", field=models.DateTimeField(auto_now_add=True, default="2026-01-01T00:00:00Z"), preserve_default=False),
        migrations.AddField(model_name="wallet", name="updated_at", field=models.DateTimeField(auto_now=True)),
        migrations.CreateModel(
            name="Withdrawal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(unique=True)),
                ("amount", models.BigIntegerField()),
                ("execute_at", models.DateTimeField()),
                ("status", models.CharField(choices=[("scheduled", "Scheduled"), ("processing", "Processing"), ("succeeded", "Succeeded"), ("failed", "Failed"), ("insufficient_funds", "Insufficient funds")], default="scheduled", max_length=24)),
                ("failure_code", models.CharField(blank=True, max_length=64)),
                ("failure_message", models.TextField(blank=True)),
                ("bank_reference", models.CharField(blank=True, max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("wallet", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="withdrawals", to="wallets.wallet")),
            ],
            options={"indexes": [models.Index(fields=["status", "execute_at"], name="wallets_wit_status_43a5ee_idx")]},
        ),
        migrations.AddField(model_name="transaction", name="balance_after", field=models.BigIntegerField(default=0)),
        migrations.AddField(model_name="transaction", name="created_at", field=models.DateTimeField(auto_now_add=True, null=True), preserve_default=False),
        migrations.AddField(model_name="transaction", name="transaction_type", field=models.CharField(choices=[("deposit", "Deposit"), ("withdrawal", "Withdrawal")], default="deposit", max_length=16)),
        migrations.AddField(model_name="transaction", name="wallet", field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name="transactions", to="wallets.wallet"), preserve_default=False),
        migrations.AddField(model_name="transaction", name="withdrawal", field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="transaction", to="wallets.withdrawal")),
        migrations.AddConstraint(model_name="wallet", constraint=models.CheckConstraint(check=models.Q(("balance__gte", 0)), name="wallet_balance_non_negative")),
        migrations.AddConstraint(model_name="transaction", constraint=models.CheckConstraint(check=models.Q(("amount__gt", 0)), name="transaction_amount_positive")),
        migrations.AddConstraint(model_name="withdrawal", constraint=models.CheckConstraint(check=models.Q(("amount__gt", 0)), name="withdrawal_amount_positive")),
    ]
