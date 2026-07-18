# Wallet Django Application

This directory contains the Django API, accounting models, application services, Celery tasks, migrations, and tests. Start with the repository [README](../README.md); the full design is documented in [docs/architecture.md](../docs/architecture.md).

## Module boundaries

- `wallet/`: Django settings, URL configuration, WSGI/ASGI, and the Celery application.
- `wallets/models.py`: wallets, withdrawals, ledger entries, bank attempts, API idempotency, and outbox events.
- `wallets/services/`: deposit, withdrawal, reservation, retry, dispatch, and outbox-publishing use cases.
- `wallets/views.py` and `serializers.py`: HTTP validation, representation, and idempotent response replay.
- `banking/client.py`: adapter for the supplied bank's real `POST /` contract.
- `wallets/tasks.py`: thin Celery entrypoints delegating to services.
- `wallets/management/commands/`: manual due-processing and reconciliation reporting.

Business logic belongs in services, not views, serializers, signals, or Celery task bodies.

## Local Python workflow

The pinned Django version requires Python 3.11 in this project.

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r wallet/requirements.txt -r third-party/requirements.txt
.venv/bin/python wallet/manage.py migrate
.venv/bin/python wallet/manage.py test wallets
```

For the complete PostgreSQL/Redis/Celery environment, use Docker Compose from the repository root:

```bash
docker compose up --build
docker compose exec wallet python manage.py migrate
docker compose exec wallet python manage.py test wallets
docker compose logs -f worker beat
```

## Financial consistency

Money is stored as integer minor units. The worker uses:

```text
available_balance = balance - reserved_balance
```

Withdrawal lock order is always withdrawal → wallet → ledger/attempt. The reservation commits before the bank request, and final settlement happens afterward in a separate transaction. No outbound HTTP request is made while holding database locks.

Ledger operations are `deposit`, `reserve`, `release`, and `complete`. `(withdrawal, operation)` is unique, preventing duplicate internal financial effects under repeated Celery delivery.

## Scheduling and delivery

Celery Beat periodically runs:

- `wallets.dispatch_due_withdrawals`: claims due scheduled or retry-due withdrawals and atomically creates outbox events.
- `wallets.publish_outbox`: publishes unpublished events and records success or publisher retry metadata.

PostgreSQL remains authoritative; Redis only transports Celery messages. Workers are at-least-once consumers and rely on row locks, state validation, and uniqueness constraints for idempotency.

## Bank failures

The bank gateway classifies results as success, confirmed failure, retryable failure, or ambiguous failure. Temporary/ambiguous results retain reserved funds and use bounded exponential retry. Exhausted attempts enter `reconciliation_required`.

The immutable internal `bank_idempotency_key` is reused for every recorded attempt, but the supplied bank cannot receive or honor it. Its lack of status lookup is why reconciliation may remain manual.

## Commands

```bash
.venv/bin/python wallet/manage.py process_due_withdrawals
.venv/bin/python wallet/manage.py reconcile_withdrawals
```

The reconciliation command lists unresolved withdrawals without changing balances because the supplied provider cannot confirm remote status.
