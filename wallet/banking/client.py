"""Small adapter around the provided third-party bank HTTP contract."""

from dataclasses import dataclass

import requests
from django.conf import settings


@dataclass(frozen=True)
class BankResult:
    outcome: str
    reference: str = ""
    code: str = ""
    message: str = ""


class RequestsBankClient:
    def deposit(self, amount: int) -> BankResult:
        try:
            response = requests.post(settings.BANK_SERVICE_URL, timeout=settings.BANK_SERVICE_TIMEOUT_SECONDS)
            payload = response.json()
        except requests.Timeout as exc:
            return BankResult("ambiguous_failure", code="read_timeout", message=str(exc))
        except requests.ConnectionError as exc:
            return BankResult("retryable_failure", code="connection_error", message=str(exc))
        except (requests.RequestException, ValueError) as exc:
            return BankResult("ambiguous_failure", code="invalid_response", message=str(exc))

        if response.status_code == 200 and payload.get("status") == 200 and payload.get("data") == "success":
            return BankResult("success", reference=response.headers.get("X-Request-ID", ""))
        if response.status_code in (429, 502, 503, 504) or payload.get("status") == 503:
            return BankResult("retryable_failure", code="bank_unavailable", message="Temporary bank failure.")
        return BankResult("confirmed_failure", code="bank_rejected", message="Bank rejected request.")
