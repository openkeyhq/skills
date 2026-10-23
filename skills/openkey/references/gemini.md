# Gemini dialect

The Gemini dialect is `POST https://api.openkey.ai/v1beta/models/{model}:generateContent`, with the key in the `x-goog-api-key` header. `{model}` is the full OpenKey id, slash included: `google/gemini-2.5-flash`. Bodies and responses are Gemini's own.

## curl

```bash
curl "https://api.openkey.ai/v1beta/models/google/gemini-2.5-flash:generateContent" \
  -H "x-goog-api-key: $OPENKEY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{"parts": [{"text": "Hello"}]}]
  }'
```

## Python with requests

```python
import os
import requests

r = requests.post(
    "https://api.openkey.ai/v1beta/models/google/gemini-2.5-flash:generateContent",
    headers={
        "x-goog-api-key": os.environ["OPENKEY_API_KEY"],
        "Content-Type": "application/json",
    },
    json={"contents": [{"parts": [{"text": "Hello"}]}]},
    timeout=60,
)
r.raise_for_status()
print(r.json()["candidates"][0]["content"]["parts"][0]["text"])
```

`httpx.post` takes the same arguments. Use the HTTP client the project already has, or `requests` or `httpx`.

## A project on a Google Gen AI SDK

This pack does not cover pointing a Google Gen AI SDK at OpenKey. Either replace its calls with the HTTP request above, using the project's existing HTTP client, or, after asking the user because it adds a dependency, use the OpenAI SDK at `https://api.openkey.ai/v1` with the same `google/…` id.

## Errors on this route

The Gemini surface answers in Google's error shape, with the `google.rpc.Code` name in `error.status`:

```json
{"error": {"code": 401, "message": "missing api key", "status": "UNAUTHENTICATED", "request_id": "…"}}
```

`error.status` is one of `INVALID_ARGUMENT`, `UNAUTHENTICATED`, `PERMISSION_DENIED`, `NOT_FOUND`, `RESOURCE_EXHAUSTED`, `FAILED_PRECONDITION`, `UNIMPLEMENTED`, `UNAVAILABLE`, `ABORTED` or `INTERNAL`. Here `error.code` is the HTTP status. Quote `error.request_id`, also sent as the `X-OpenKey-Request-Id` response header, to support.
