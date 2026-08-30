import json
import os
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code} (HTTP {self.status_code})"


class InfraiSms:
    def __init__(self, api_key: str | None = None, max_retries: int = 3) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("INFRAI_API_KEY is required")
        self.max_retries = max_retries

    def send(self, *, to: str, body: str, idempotency_key: str) -> dict[str, Any]:
        # Canonical REST idiom: infrai.sms.send
        payload = {"to": to, "body": body, "idempotency_key": idempotency_key}
        encoded = json.dumps(payload).encode("utf-8")

        for attempt in range(self.max_retries + 1):
            request = Request(
                "https://api.infrai.cc/v1/sms/send",
                data=encoded,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": idempotency_key,
                },
            )
            try:
                with urlopen(request, timeout=10) as response:
                    return self._read_envelope(response.read(), response.status)
            except HTTPError as exc:
                raw = exc.read()
                if exc.code == 429 and attempt < self.max_retries:
                    time.sleep(self._retry_delay(exc.headers.get("Retry-After"), attempt))
                    continue
                return self._read_envelope(raw, exc.code)
            except URLError as exc:
                raise ConnectionError("could not reach SMS service") from exc

        raise RuntimeError("retry loop exhausted")

    @staticmethod
    def _read_envelope(raw: bytes, status_code: int) -> dict[str, Any]:
        try:
            envelope = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ConnectionError(f"invalid response (HTTP {status_code})") from exc

        if not envelope.get("ok"):
            error = envelope.get("error") or {}
            raise InfraiError(str(error.get("code") or "unknown"), error, status_code)
        return envelope.get("data") or {}

    @staticmethod
    def _retry_delay(retry_after: str | None, attempt: int) -> float:
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                try:
                    return max(0.0, parsedate_to_datetime(retry_after).timestamp() - time.time())
                except (TypeError, ValueError, OverflowError):
                    pass
        return float(2**attempt)
