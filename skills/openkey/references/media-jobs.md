# Images, videos, batches and webhooks

## Contents

- Images: synchronous
- Videos: a job you poll
- Batches and background chat
- Webhooks

All of these use the OpenAI-dialect base `https://api.openkey.ai/v1` and `Authorization: Bearer $OPENKEY_API_KEY`. `openkey/auto` is refused on images and videos: name a model whose `output_modalities` include `image` or `video` in the public catalog, `GET https://api.openkey.ai/api/public/v1/models`. Full request schemas: `https://openkey.ai/openapi/openkey.yaml`.

## Images: synchronous

`POST /v1/images/generations` speaks the OpenAI Images wire and answers in the same request. OpenKey does not store the image: the response carries it as `b64_json`. A chat-only model answers `404 model_not_found`.

```python
import base64

img = client.images.generate(model="openai/gpt-image-1", prompt="a red cube")
with open("cube.png", "wb") as f:
    f.write(base64.b64decode(img.data[0].b64_json))
```

```bash
curl https://api.openkey.ai/v1/images/generations \
  -H "Authorization: Bearer $OPENKEY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"openai/gpt-image-1","prompt":"a red cube"}'
```

## Videos: a job you poll

`POST /v1/videos` answers `202` with a job and a `Location` header. `Location` is a path: resolve it against the URL the response actually came from, after any redirect (`urljoin(r.url, r.headers["Location"])`), not against a base you hard-coded. Poll it until the `X-OpenKey-Job-Status` header is terminal: `succeeded`, `failed`, `cancelled` or `expired` (non-terminal: `queued`, `running`). Branch on that header, not the body: the body keeps the Sora statuses (`queued`, `in_progress`, `completed`, `failed`), so a cancelled or expired video says `failed` there. `Retry-After` on a poll is the spacing to wait. The MP4 is at `/v1/videos/{id}/content` and answers `409 job_not_ready` until the job succeeded. `seconds` is a string on the wire (`"8"`).

`X-OpenKey-Idempotency-Key` makes the create safe to retry: the same key returns the first job, with `X-OpenKey-Idempotent-Replay: true`. Only `POST /v1/videos` accepts it.

```python
import os
import time
from urllib.parse import urljoin

import requests

BASE = "https://api.openkey.ai"
AUTH = {"Authorization": f"Bearer {os.environ['OPENKEY_API_KEY']}"}

def make_video(video_model: str, prompt: str, idempotency_key: str) -> bytes:
    r = requests.post(
        f"{BASE}/v1/videos",
        headers={**AUTH, "X-OpenKey-Idempotency-Key": idempotency_key},
        json={"model": video_model, "prompt": prompt},
        timeout=60,
    )
    r.raise_for_status()
    job_url = urljoin(r.url, r.headers["Location"])
    while True:
        r = requests.get(job_url, headers=AUTH, timeout=60)
        r.raise_for_status()
        status = r.headers.get("X-OpenKey-Job-Status")
        if status in ("succeeded", "failed", "cancelled", "expired"):
            break
        time.sleep(float(r.headers.get("Retry-After", "5")))
    if status != "succeeded":
        raise RuntimeError(f"video job {status}: {r.json().get('error')}")
    r = requests.get(f"{job_url}/content", headers=AUTH, timeout=300)
    r.raise_for_status()
    return r.content
```

## Batches and background chat

- `POST /v1/batches` answers `202` and `Location`, like a video. The body has `endpoint`, `completion_window`, optional `metadata`, and either inline `requests` or an `input_file_id` from `POST /v1/files` (multipart `file` and `purpose`), not both. Poll `/v1/batches/{id}` on `X-OpenKey-Job-Status`; line results are at `/v1/batches/{id}/output` (`409 job_not_ready` until done).
- A failed line becomes an error line in the output, and budgets still apply per line (`quota_exceeded`), while per-key rate limits do not.
- Batch create takes no idempotency key: a retried create submits and bills a second batch, so never retry it automatically.
- A non-streaming chat call with `X-OpenKey-Background: true` answers `202` with a job at `/v1/jobs/{id}` instead of holding the connection; it follows the same protocol.

## Webhooks

Instead of polling, register an HTTPS endpoint once for terminal job events (`succeeded`, `failed`, `cancelled`, `expired`) of every kind: `POST /v1/webhooks` with `url`, and optionally `description`, `kinds` (`video`, `batch`, `completion`; omitted means all) and `disabled`. Unknown fields are a `400`. The create response (and a rotate, `POST /v1/webhooks/{id}/rotate`) is the only time the signing secret, starting `whsec_`, is shown: store it in the app's own secret store or environment.

Each delivery carries `X-OpenKey-Signature: t=<unix seconds>,v1=<hex>[,v1=<hex>]`: one lowercase-hex HMAC-SHA256 of `<t>.<raw body>` per signing secret, keyed with the whole secret, `whsec_` included. During a rotation the old and the new secret both sign (24 hours by default), so the header carries several `v1` values: accept the delivery if any of them matches. Verify against the raw body bytes, reject a `t` more than 5 minutes off in either direction, compare in constant time, and de-duplicate on `X-OpenKey-Event-Id`, because delivery is at least once.

```python
import hashlib
import hmac
import time

def verify(raw_body: bytes, signature_header: str, secret: str, tolerance_s: int = 300) -> bool:
    pairs = [[s.strip() for s in p.split("=", 1)] for p in signature_header.split(",") if "=" in p]
    t = next((v for k, v in pairs if k == "t"), "")
    v1s = [v for k, v in pairs if k == "v1"]
    if not t.isdigit() or not v1s or abs(time.time() - int(t)) > tolerance_s:
        return False
    expected = hmac.new(secret.encode(), f"{t}.".encode() + raw_body, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, v) for v in v1s)
```
