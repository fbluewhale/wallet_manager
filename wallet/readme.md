# Wallet Service

A Django wallet service using integer minor units for every monetary amount.

## Architecture

- `wallets.models`: wallets, scheduled withdrawals, and immutable-style transaction history.
- `wallets.services`: transactional deposit, scheduling, and single-worker withdrawal execution.
- `banking.client`: adapter for the provided bank service (`POST /`, success is JSON `{"data":"success","status":200}`).
- `process_due_withdrawals`: sequential management command for due withdrawals.

Views only validate and serialize HTTP requests; business rules live in services. A bank client can be injected into `execute_withdrawal` in tests.

## Setup and commands

From the repository root:

```bash
./run-dev.sh
# or: docker compose up --build
```

Run migrations and tests manually:

```bash
.venv/bin/python wallet/manage.py migrate
.venv/bin/python wallet/manage.py test wallets
.venv/bin/python wallet/manage.py process_due_withdrawals
```

## API

- `POST /wallets/` — create a wallet.
- `GET /wallets/{wallet_uuid}/` — retrieve wallet details.
- `POST /wallets/{wallet_uuid}/deposit` with `{"amount": 100}` — deposit minor units.
- `POST /wallets/{wallet_uuid}/withdraw` with `{"amount": 100, "execute_at": "2026-07-18T12:00:00Z"}` — schedule a withdrawal (202).
- `GET /wallets/withdrawals/{withdrawal_uuid}/` — retrieve withdrawal details.

## Milestone 1 limitations

This version assumes one withdrawal worker. It has no automatic scheduler, concurrent-worker coordination, retries, reservation balance, API idempotency, crash recovery, or ambiguous network-result reconciliation. A bank failure or network error marks the withdrawal failed and leaves the wallet balance unchanged.
