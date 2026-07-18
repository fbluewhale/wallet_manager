# Wallet Service

A Django wallet service using integer minor units for every monetary amount.

## Architecture

- `wallets.models`: wallets, scheduled withdrawals, and immutable-style transaction history.
- `wallets.services`: transactional deposit, scheduling, execution, and database-backed dispatch.
- `banking.client`: adapter for the provided bank service (`POST /`, success is JSON `{"data":"success","status":200}`).
- Celery Beat runs the dispatcher every `DISPATCHER_INTERVAL_SECONDS` (five seconds by default); Celery workers execute claimed withdrawals.

Views only validate and serialize HTTP requests; business rules live in services. A bank client can be injected into `execute_withdrawal` in tests.

## Setup and commands

From the repository root:

```bash
docker compose up --build
```

Run migrations and tests manually:

```bash
.venv/bin/python wallet/manage.py migrate
.venv/bin/python wallet/manage.py test wallets
.venv/bin/python wallet/manage.py process_due_withdrawals
docker compose logs -f worker
docker compose logs -f beat
```

## API

- `POST /wallets/` — create a wallet.
- `GET /wallets/{wallet_uuid}/` — retrieve wallet details.
- `POST /wallets/{wallet_uuid}/deposit` with `{"amount": 100}` — deposit minor units.
- `POST /wallets/{wallet_uuid}/withdraw` with `{"amount": 100, "execute_at": "2026-07-18T12:00:00Z"}` — schedule a withdrawal (202).
- `GET /wallets/withdrawals/{withdrawal_uuid}/` — retrieve withdrawal details.

## Automatic scheduling

The database is the source of truth. Beat periodically finds due `scheduled` records, claims a bounded batch by moving them to `queued`, and publishes a task after that transaction commits. Workers accept `scheduled`/`queued` work, transition it to `processing`, and the existing terminal state check prevents a duplicated task from debiting twice.

If a process dies after the database commit but before task publishing, the next scan recovers `queued` records older than `WITHDRAWAL_MAX_QUEUED_AGE_SECONDS` and dispatches them again.

## Milestone 2 limitations

There is no transactional outbox, retry policy, reservation balance, API idempotency, crash recovery, or ambiguous network-result reconciliation. Multi-dispatcher claim handling is intentionally basic; workers still serialize on the withdrawal row and terminal statuses prevent a second debit.
