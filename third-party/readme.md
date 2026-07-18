# Provided Third-Party Bank Simulator

This Flask application is the bank simulator supplied with the challenge. The wallet service treats it as an external dependency and does not modify its contract.

## Run directly

Use Python 3.11 and install its dependencies:

```bash
.venv/bin/pip install -r third-party/requirements.txt
.venv/bin/python third-party/app.py
```

It listens on `0.0.0.0:8010`. The repository Docker Compose stack starts it automatically and exposes `http://localhost:8010`.

## Actual API contract

The application exposes one endpoint:

```http
POST /
```

It accepts no required request body. After an artificial one-second delay it returns HTTP 200 with one of these JSON payloads:

```json
{"data": "success", "status": 200}
```

```json
{"data": "failed", "status": 503}
```

The second result represents temporary inability to process the request; `503` is inside the JSON body rather than the HTTP status code. The failure probability is controlled by the source-level `ERROR_RATE`, currently `0.1`.

Example:

```bash
curl -X POST http://localhost:8010/
```

## Important limitations

The simulator does not support:

- an idempotency key in a header or body;
- an external transaction/reference ID;
- transfer-status lookup;
- deterministic failure selection through its API;
- confirmed permanent business rejections.

Consequently, a timeout or lost connection after request transmission is ambiguous. The wallet keeps funds reserved, retries with its same internal key for audit consistency, and eventually marks unresolved work `reconciliation_required`; the bank itself cannot guarantee exactly-once payout.
