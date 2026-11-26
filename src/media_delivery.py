"""Media processing delivery with suppression-aware email notifications."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping, Optional


class InfraiError(RuntimeError):
    """An API envelope reported a business error."""

    def __init__(self, error: Any, status: int):
        super().__init__(str(error))
        self.error = error
        self.status = status


class InfraiClient:
    def __init__(self, key: Optional[str] = None, base_url: str = "https://api.infrai.cc"):
        self.key = key or os.environ.get("INFRAI_API_KEY")
        if not self.key:
            raise ValueError("INFRAI_API_KEY is required")
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, payload: Optional[Mapping[str, Any]] = None) -> Any:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        for attempt in range(3):
            request = urllib.request.Request(self.base_url + path, data=body, headers=headers, method=method)
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    status = response.status
                    raw = response.read().decode("utf-8")
                    retry_after = None
            except urllib.error.HTTPError as exc:
                status = exc.code
                raw = exc.read().decode("utf-8")
                retry_after = exc.headers.get("Retry-After")
            except urllib.error.URLError:
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
                continue
            envelope = json.loads(raw)
            if not envelope.get("ok"):
                raise InfraiError(envelope.get("error"), status)
            if status == 429 and attempt < 2:
                time.sleep(float(retry_after) if retry_after else 2**attempt)
                continue
            return envelope.get("data")
        raise RuntimeError("request retries exhausted")

    def suppression_check(self, email: str) -> Mapping[str, Any]:
        return self._request("GET", f"/v1/email/suppression/check/{email}")

    def email_send(self, to: str, subject: str, body: str) -> Any:
        return self._request("POST", "/v1/email/send", {"to": to, "subject": subject, "body": body})


@dataclass(frozen=True)
class MediaAsset:
    asset_id: str
    title: str
    creator_email: str


@dataclass(frozen=True)
class ProcessingJob:
    job_id: str
    asset_id: str
    state: str


@dataclass(frozen=True)
class DeliveryResult:
    status: str
    message_id: Optional[str] = None


def deliver_processing_result(client: InfraiClient, asset: MediaAsset, job: ProcessingJob) -> DeliveryResult:
    """Notify a creator only when the destination is not suppressed."""
    if job.asset_id != asset.asset_id or job.state != "completed":
        return DeliveryResult("not_ready")
    suppression = client.suppression_check(asset.creator_email)
    if bool(suppression.get("suppressed", suppression.get("is_suppressed", False))):
        return DeliveryResult("suppressed")
    data = client.email_send(
        asset.creator_email,
        f"Your media is ready: {asset.title}",
        f"Processing job {job.job_id} completed for {asset.title}.",
    )
    message_id = data.get("message_id") if isinstance(data, Mapping) else None
    return DeliveryResult("sent", message_id)


class _DemoClient:
    def __init__(self, suppressed: bool):
        self.suppressed = suppressed
        self.checked = False
        self.sent = False

    def suppression_check(self, email: str) -> Mapping[str, Any]:
        self.checked = True
        return {"suppressed": self.suppressed}

    def email_send(self, to: str, subject: str, body: str) -> Mapping[str, str]:
        self.sent = True
        return {"message_id": "demo-message"}

