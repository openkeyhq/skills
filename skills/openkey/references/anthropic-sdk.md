# Anthropic SDK and the Messages API

The Anthropic dialect is `POST /v1/messages` on the bare host `https://api.openkey.ai`. The SDK appends `/v1/messages` itself, so the base URL has no `/v1`: with `https://api.openkey.ai/v1` the SDK posts to `/v1/v1/messages` and gets a 404. The SDK sends `api_key` / `apiKey` as the `x-api-key` header. Request and response bodies are Anthropic's own; only the model id changes, to `provider/model`, and models from other labs work through this client too.

## Python

```python
import os
from anthropic import Anthropic

client = Anthropic(
    base_url="https://api.openkey.ai",
    api_key=os.environ["OPENKEY_API_KEY"],
)
msg = client.messages.create(
    model="anthropic/claude-sonnet-4.5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}],
)
print(msg.content[0].text)
```

Streaming uses the SDK's own helper, unchanged:

```python
with client.messages.stream(
    model="anthropic/claude-sonnet-4.5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}],
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

## TypeScript

```ts
import Anthropic from "@anthropic-ai/sdk";

// Unset, an undefined apiKey would make the SDK fall back to ANTHROPIC_API_KEY.
const apiKey = process.env.OPENKEY_API_KEY;
if (!apiKey) throw new Error("OPENKEY_API_KEY is not set");

const client = new Anthropic({
  baseURL: "https://api.openkey.ai",
  apiKey,
});
const msg = await client.messages.create({
  model: "anthropic/claude-sonnet-4.5",
  max_tokens: 1024,
  messages: [{ role: "user", content: "Hello" }],
});
console.log(msg.content);
```

## curl

```bash
curl https://api.openkey.ai/v1/messages \
  -H "x-api-key: $OPENKEY_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "anthropic/claude-sonnet-4.5",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## Errors on this route

`/v1/messages` answers in Anthropic's error shape and vocabulary, so the SDK raises its usual typed exceptions:

```json
{"type": "error", "error": {"type": "authentication_error", "message": "missing api key", "request_id": "…"}}
```

- `error.type` is one of Anthropic's values: `invalid_request_error`, `authentication_error`, `permission_error`, `not_found_error`, `request_too_large`, `rate_limit_error`, `billing_error`, `timeout_error`, `api_error`, `overloaded_error`.
- These bodies carry no OpenKey `code` and no `doc_url`: only Anthropic's vocabulary. Branch on the exception class or `error.type`. The errors docs page says `code` is the same on every route; production does not send it here.
- Quote `error.request_id`, also sent as the `X-OpenKey-Request-Id` response header, to support.
- A `401` is always about the OpenKey key, never a provider outage.
