# X-OpenKey headers

## Contents

- Sending headers from an SDK
- Attribution: who a request was for
- Usage and balance disclosure
- Response headers
- Reading response headers from an SDK

OpenKey reports what happened to a request in response headers, and a header that is present means the thing happened. Every request header below is optional. Browsers cannot send or read `X-OpenKey-*` headers (CORS allows only `Authorization` and `Content-Type` and exposes none), so all of this is server-side code.

## Sending headers from an SDK

| Client | Per call | On every call |
|---|---|---|
| OpenAI or Anthropic SDK, Python | `extra_headers={...}` | `default_headers={...}` on the client |
| OpenAI or Anthropic SDK, TypeScript | request options `{ headers: {...} }` | `defaultHeaders: {...}` on the client |
| `openai-go` | `option.WithHeader(name, value)` | the same option on `openai.NewClient` |
| HTTP | a request header | |

```python
completion = client.chat.completions.create(
    model="openai/gpt-4o",
    messages=[{"role": "user", "content": "Hello"}],
    extra_headers={"X-OpenKey-Customer": "acme-corp", "X-OpenKey-Tags": "project=atlas"},
)
```

## Attribution: who a request was for

Reporting only: these never affect authentication, routing, budgets or price.

| Header | Value |
|---|---|
| `X-OpenKey-Customer` | Your own customer id: at most 64 characters of `A-Za-z0-9._:@-` |
| `X-OpenKey-User` | Your own end-user id, same characters |
| `X-OpenKey-Tags` | `key=value` pairs separated by commas, at most 5. A key is at most 32 characters of `a-z0-9._-`; a value follows the customer-id rule. `project` is the reserved key with its own report column |

A value that breaks these rules is dropped whole, never truncated, and the drop is named in `X-OpenKey-Warning`. The request still succeeds.

## Usage and balance disclosure

Only `true` or `1` (any case) turns these on; any other value leaves them off.

| Header | Effect |
|---|---|
| `X-OpenKey-Include-Usage: true` | Adds `X-OpenKey-Usage` on keys that have no budget |
| `X-OpenKey-Include-Balance: true` | Adds `X-OpenKey-Balance-Remaining` when a balance exists |

## Response headers

Money is integer micro-USD (1 USD = 1,000,000). A missing budget header means the key has no budget, never zero.

| Header | When | Value |
|---|---|---|
| `X-OpenKey-Request-Id` | Inference responses (chat, Messages, Responses, Gemini, embeddings), errors included | The id to log and quote to support. Opaque: do not parse it |
| `X-Request-ID` | Every response | Transport correlation id |
| `X-OpenKey-Budget-Limit` | The key has a hard budget | The window's ceiling |
| `X-OpenKey-Budget-Used` | With Limit | Spend in the window before this request |
| `X-OpenKey-Budget-Remaining` | With Limit | What is left, never below 0 |
| `X-OpenKey-Usage` / `X-OpenKey-Usage-Window` | A budgeted key, or `Include-Usage` | Spend so far; window `day`, `month` or `total` |
| `X-OpenKey-Balance-State` | The account is known | `ok`, `low`, `empty` or `suspended` |
| `X-OpenKey-Auto-Route` | The model was `openkey/auto` | `<route>=<id>` of the model that ran |
| `X-OpenKey-Variant` | A `:nitro`, `:floor`, `:online` or `:free` suffix changed routing | The suffix name |
| `X-OpenKey-Warning` | Something non-fatal was dropped or reinterpreted | Comma-separated codes |

`X-OpenKey-Warning` codes are open-ended: log a code you do not recognise and carry on, never fail on it. Today's families include `provider_prefs_headers_ignored`, `prompt_log_unavailable` and the attribution drops (`attribution_customer_dropped`, `attribution_user_dropped`, `attribution_tag_dropped`, `attribution_tags_overflow`, …). A code names what was dropped, never the value.

The budget trio also comes on image and video-create responses. On a streamed call, every header is sent before the first chunk.

## Reading response headers from an SDK

The SDKs return the parsed body by default; ask for the raw response to see headers.

```python
raw = client.chat.completions.with_raw_response.create(
    model="openai/gpt-4o",
    messages=[{"role": "user", "content": "Hello"}],
)
request_id = raw.headers.get("x-openkey-request-id")
warnings = [w for w in raw.headers.get("x-openkey-warning", "").split(",") if w]
completion = raw.parse()
```

```ts
const { data, response } = await client.chat.completions
  .create({ model: "openai/gpt-4o", messages: [{ role: "user", content: "Hello" }] })
  .withResponse();
const requestId = response.headers.get("x-openkey-request-id");
```

The Anthropic Python SDK has the same `with_raw_response`.
