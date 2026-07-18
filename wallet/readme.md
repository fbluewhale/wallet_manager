# Wallet Service

> The complete, implementation-specific guide is [docs/architecture.md](../docs/architecture.md), with an editable [Draw.io diagram](../docs/wallet-architecture.drawio).

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
.venv/bin/python wallet/manage.py reconcile_withdrawals
```

## API

- `POST /wallets/` — create a wallet.
- `GET /wallets/{wallet_uuid}/` — retrieve wallet details.
- `POST /wallets/{wallet_uuid}/deposit` with `{"amount": 100}` — deposit minor units.
- `POST /wallets/{wallet_uuid}/withdraw` with `{"amount": 100, "execute_at": "2026-07-18T12:00:00Z"}` — schedule a withdrawal (202).
- `GET /wallets/withdrawals/{withdrawal_uuid}/` — retrieve withdrawal details.

## Automatic scheduling

The database is the source of truth. Beat periodically finds due `scheduled` records, claims a bounded batch by moving them to `queued`, and writes a durable outbox event in the same transaction. A separate periodic publisher sends outbox events to Celery and records `published_at`. Workers accept `scheduled`/`queued` work, transition it to `processing`, and terminal-state checks prevent a duplicated task from debiting twice.

If a process dies after the database commit but before task publishing, the unpublished outbox event remains for a later publisher. Stale `queued` records older than `WITHDRAWAL_MAX_QUEUED_AGE_SECONDS` are recovered for dispatch.

## Consistency and reservations

`available_balance = balance - reserved_balance`. At execution, the worker locks the withdrawal and then its wallet, reserves available funds and records an immutable reservation entry, then commits. The bank request occurs outside every database transaction. A second short transaction either settles the reservation (reducing both balances) or releases it (reducing `reserved_balance` only).

The database enforces `balance >= 0`, `reserved_balance >= 0`, and `reserved_balance <= balance`. Every flow uses the same lock order: withdrawal, wallet, ledger. Dispatcher claims use PostgreSQL `FOR UPDATE SKIP LOCKED`, so separate scheduler instances can claim different rows in parallel.

The test suite exercises ledger idempotency and competing withdrawals; run PostgreSQL-backed integration checks with `docker compose up --build` and `docker compose exec wallet python manage.py test wallets`.

## Bank failures and retries

The provided bank exposes only `POST /` and replies with JSON success (`data=success`, `status=200`) or a temporary failure (`data=failed`, `status=503`). It accepts no idempotency key, has no transfer ID or status lookup, and its random failure simulation is not deterministic.

Each withdrawal nevertheless has one immutable `bank_idempotency_key`; every internal retry and append-only `BankTransferAttempt` reuses it. Confirmed failures release reservations. Temporary failures, connection failures, malformed responses, and timeouts keep funds reserved and enter `retry_pending` with bounded exponential backoff (`BANK_RETRY_BASE_SECONDS`, `BANK_RETRY_MAX_SECONDS`, `BANK_MAX_RETRIES`). Exhausted attempts enter `reconciliation_required`.

Because the supplied bank does not honor an idempotency key or offer status lookup, an ambiguous timeout after transmission cannot prove whether it paid. Funds remain reserved and manual reconciliation is required; automatic retry may still risk a duplicate external payout.

## Configuration and operations

Copy `.env.example` to `.env` for local configuration. Production requires `DJANGO_SECRET_KEY` and defaults `DJANGO_DEBUG` to false. Configure database, Redis, bank URL/timeouts, scheduler batches, retry limits, allowed hosts, request size, and log level only through environment variables.

`reconcile_withdrawals` lists `reconciliation_required` records for manual handling. The supplied bank cannot confirm remote status, so the command deliberately does not mutate unresolved funds.

See [the detailed architecture guide](../docs/architecture.md) and its editable Draw.io diagram for component and flow views.

## Milestone 2 limitations

There is no transactional outbox, retry policy, reservation balance, API idempotency, crash recovery, or ambiguous network-result reconciliation. Multi-dispatcher claim handling is intentionally basic; workers still serialize on the withdrawal row and terminal statuses prevent a second debit.
