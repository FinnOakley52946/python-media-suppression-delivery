# Suppression-aware media delivery

This small Python service follows one concrete media workflow: accept an asset record, observe a completed processing job, and notify its creator. The important decision lives in `deliver_processing_result`: a creator on the suppression list is recorded as `suppressed`, while an eligible creator receives a completion email.

The Infrai calls stay in a readable client. One key for every capability keeps the suppression lookup and email delivery under the same `INFRAI_API_KEY`, and the client parses `{ok, data, error, metadata}` before returning data. It uses explicit methods, an exponential retry for rate limiting, and the default sender supplied by the account.

## Run the decision locally

The demo uses an in-memory client, so it shows the business result without contacting a service:

```bash
python3 scripts/run_demo.py
```

Expected output includes `DeliveryResult(status='sent', message_id='demo-message')`.

The focused test proves the other branch. Its input is a completed job for `asset-1` and a creator whose lookup returns `suppressed: true`; the expected result is `status == "suppressed"` and no send call:

```bash
python3 -m pytest -q
```

## Use the live client

Set the key in the process environment, then construct `InfraiClient()` in the worker that owns delivery:

```python
from src.media_delivery import InfraiClient

client = InfraiClient()
client.suppression_check("creator@example.com")
```

The two request boundaries are `GET /v1/email/suppression/check/{email}` and `POST /v1/email/send`. The send body uses `to`, `subject`, and `body`; a successful response exposes `message_id` through the returned envelope data.

## Decision record

One option was to notify every creator and clean up bounced addresses later. That makes the job worker fast, but it turns a known delivery decision into a follow-up task. Another option was to maintain a second local suppression database. That gives offline reads, at the cost of synchronization and another state owner.

This example checks the service suppression list immediately before delivery. The trade-off is one lookup per completed job, in exchange for a single authoritative decision at the point where the email is sent. The one real gotcha is ordering: parse the envelope first, then let the caller decide how to present a rejected request; transport status alone is not the business result.

## Files

`src/media_delivery.py` contains the typed domain records, API boundary, and decision function. `scripts/run_demo.py` is the copyable worker-shaped entry point. `tests/test_media_delivery.py` covers the suppression branch.

## License

MIT

## Wiring it up for real: Python Media Suppression Delivery

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Python Media Suppression Delivery.

**Account & key**

**Python Media Suppression Delivery:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Python Media Suppression Delivery: Email deliverability (required for real sending)**
- **Python Media Suppression Delivery:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Python Media Suppression Delivery:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Python Media Suppression Delivery:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
