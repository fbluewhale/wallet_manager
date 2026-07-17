"""Small adapter around the provided third-party bank HTTP contract."""

from dataclasses import dataclass

import requests
from django.conf import settings


@dataclass(frozen=True)
class BankResult:
    succeeded: bool
    reference: str = ""
    code: str = ""
    message: str = ""


class RequestsBankClient:
    def deposit(self, amount: int) -> BankResult:
        try:
            response = requests.post(settings.BANK_SERVICE_URL, timeout=settings.BANK_SERVICE_TIMEOUT_SECONDS)
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            return BankResult(False, code="bank_unavailable", message=str(exc))

        if response.status_code == 200 and payload.get("status") == 200 and payload.get("data") == "success":
            return BankResult(True, reference=response.headers.get("X-Request-ID", ""))
        return BankResult(False, code="bank_rejected", message=str(payload.get("data", "Bank rejected request.")))
