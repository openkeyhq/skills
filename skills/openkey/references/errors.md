# OpenKey errors

## Contents

- The envelope
- The seven types
- Codes, and what to do
- Retry rules
- Errors inside a stream
- Other dialects

Every code has a section at `https://openkey.ai/docs/errors#<code>`; fetch it when a code here is not enough. A `4xx` is about the request or the account and says specifically why. A `5xx` is the platform or an exhausted provider path and is deliberately generic: a fixed sentence and a request id.

## The envelope

The OpenAI-dialect inference routes (`/v1/chat/completions`, `/v1/responses`, `/v1/embeddings`) answer:

```json
{"error": {"message": "missing api key", "type": "authentication_error", "code": "unauthorized", "request_id": "…"}}
```

The control plane, OpenKey's management routes, answers the fuller shape, which adds `doc_url` and `region`. Some `/v1` job routes (`/v1/batches`, `/v1/jobs`, `/v1/webhooks`) use it too:

```json
{"error": {"type": "authentication_error", "code": "unauthorized", "message": "missing api key", "request_id": "…", "region": "eu", "doc_url": "https://openkey.ai/docs/errors#unauthorized"}}
```

Parse `error.code` and `error.message` on every route, and `error.type` when present; never assume one route's extra fields on another.

| Field | Meaning |
|---|---|
| `type` | One of seven classes, a closed set. Branch on it |
| `code` | The precise reason. Diagnose on it. A code you do not know is a generic failure of its HTTP status class, never a crash |
| `message` | For humans: specific on a `4xx`, a fixed sentence plus the request id on a `5xx` |
| `request_id` | Opaque; quote it to support. On inference routes it equals the `X-OpenKey-Request-Id` header. It can be absent, for example on some `401`s (`/v1/videos`); then quote the `X-Request-ID` response header |
| `param` | `4xx` only, when one request field is to blame |
| `doc_url`, `region` | Control-plane shape only: a link to `…/docs/errors#<code>`, and which region answered |
| `provider` | The provider that failed, when there is one |
| `metadata` | Structured detail, such as which budget stopped the request |

## The seven types

| `type` | Means | The fix |
|---|---|---|
| `invalid_request_error` | The request is wrong, or names something that is not there | Change the request |
| `authentication_error` | No valid OpenKey key | Present a valid key; never a provider outage |
| `permission_error` | Known caller, not allowed | A different grant; a better key does not help |
| `rate_limit_error` | Too much, too fast, or an allowance spent for now | Wait |
| `billing_error` | OpenKey credit, budget or billing | A top-up or a billing change |
| `upstream_error` | The failure is at a provider | Usually at the provider |
| `api_error` | OpenKey's side | Nothing on yours; retry, then quote the request id |

## Codes, and what to do

| Code | Status | Do |
|---|---|---|
| `invalid_request` | 400 (also 413) | Fix the field named in `message` or `param`; resending unchanged fails the same way |
| `content_blocked` | 400 | A workspace guardrail refused it; remove the named content or ask an owner |
| `model_not_found` | 404 | Copy the id exactly from `GET https://api.openkey.ai/v1/models`, provider prefix included |
| `not_found` | 404 | Check the id in the URL against the list route |
| `job_not_ready` | 409 | Poll the job until it is terminal, then fetch its output |
| `result_expired` | 410 | Run the job again; download results when they complete |
| `unauthorized` | 401 | Fix or replace the OpenKey key in `OPENKEY_API_KEY` |
| `forbidden` | 403 | The key or member lacks the permission; ask a workspace owner |
| `rate_limited` | 429 | Back off: honour `Retry-After`, add jitter |
| `free_quota_exceeded` | 429 | The daily `:free` allowance is spent; wait for `X-OpenKey-Free-Reset` (next UTC midnight) or use a paid model |
| `insufficient_credit` | 402 | Add credit in the OpenKey app |
| `quota_exceeded` | 402 (also 429) | A key, member or team budget is spent; raise it, wait for the window, or send a smaller `max_tokens` |
| `billing_suspended` | 402 | Settle the account's billing |
| `plan_required` | 402 | The plan lacks the feature |
| `provider_credits_exhausted` | 429 | The user's own provider key (BYOK) is out of credit; top up at that provider. Waiting never fixes it |
| `upstream_error` | 400 | The provider refused the request; act on its message in `message` (context too long, unsupported parameter) |
| `upstream_unavailable` | 503 | Every provider for the model failed; retry with backoff, or choose another model |
| `internal_error` | 500 | Retry; if it persists, quote the request id |
| `not_implemented` | 501 | Not supported here; use the documented alternative |

## Retry rules

- Retry `429 rate_limited` after `Retry-After`, with jitter, and `5xx` with exponential backoff and a cap.
- Never retry `provider_credits_exhausted`, `free_quota_exceeded` before its reset, any `401`, `402`, `403` or `404`, or a `400` unchanged.
- Upstream statuses are mapped once by the gateway: a provider `4xx` becomes `400 upstream_error`, a provider `5xx` becomes `503 upstream_unavailable`, a provider `429` becomes `429 rate_limited`. Do not re-map them in client code.
- Branch on `code`, not on the status. The OpenAI and Anthropic SDKs retry every `429` and `5xx` twice by default, so they also re-send `provider_credits_exhausted`, `free_quota_exceeded` and a `429 quota_exceeded`, which waiting never fixes. Where that matters, turn the SDK's retries off (`max_retries=0` in Python, `maxRetries: 0` in TypeScript, on the client or per call) and retry yourself only on `rate_limited` and `5xx` codes. The OpenAI SDKs expose the code as `err.code` on their API errors. Never stack your own retry loop on top of the SDK's default one.

## Errors inside a stream

Once a stream has started the status stays `200`, and a failure arrives as an event:

```
data: {"error":{"message":"…","type":"upstream_error","code":"upstream_unavailable","request_id":"…"}}

data: [DONE]
```

- Any `data:` JSON with a top-level `error` ends the call as a failure; the `[DONE]` after it does not clear it.
- Its `type` and `code` are the ones the failure would have had before the first byte.
- Do not retry automatically: part of the answer was already delivered.
- A stream that ends with neither `[DONE]` nor a final chunk is incomplete, not a success.
- On `/v1/responses` streams the error event's `type` is the event name; branch on `code`.

## Other dialects

- `/v1/messages` answers in Anthropic's shape, `{"type": "error", "error": {"type": …, "message": …, "request_id": …}}`, with no OpenKey `code`: only Anthropic's types (`invalid_request_error`, `authentication_error`, `permission_error`, `not_found_error`, `request_too_large`, `rate_limit_error`, `billing_error`, `timeout_error`, `api_error`, `overloaded_error`), so the Anthropic SDK raises its usual exceptions.
- The Gemini surface answers in Google's shape, `{"error": {"code": <HTTP status>, "message": …, "status": …, "request_id": …}}`, with the `google.rpc.Code` name in `status` (`INVALID_ARGUMENT`, `UNAUTHENTICATED`, `PERMISSION_DENIED`, `NOT_FOUND`, `RESOURCE_EXHAUSTED`, `UNAVAILABLE`, `INTERNAL`, …).
- Neither carries `doc_url`. Quote `request_id` or the `X-OpenKey-Request-Id` header either way.
