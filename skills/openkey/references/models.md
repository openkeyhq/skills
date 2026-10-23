# Model ids and the catalog

## Contents

- Id grammar
- `openkey/auto`
- Suffixes
- Catalog commands
- Prices

## Id grammar

- Every id is `provider/model`, lab first: `openai/gpt-4o`, `anthropic/claude-sonnet-4.5`, `google/gemini-2.5-flash`, `deepseek/deepseek-chat`, `openai/text-embedding-3-small`, `openai/gpt-image-1`.
- A bare upstream name is not an id here. `gpt-4o` becomes `openai/gpt-4o`; `claude-sonnet-4.5` becomes `anthropic/claude-sonnet-4.5`.
- The prefix is the catalog's lab slug, which often differs from the brand: Llama models are under `meta-llama/`, Grok under `x-ai/`, Mistral under `mistralai/`. Never guess one; look it up.
- Some models are listed under more than one spelling, for example with dots or dashes in the version. Copy the id exactly as the catalog lists it.
- Ids starting with `~` are aliases that always point at the latest model of a family, for example `~openai/gpt-latest`. Use one only when the user wants "always the latest"; the model behind it changes without notice.
- Confirm an id in the catalog before writing it into code (commands below); the lookup is free and needs no key. If you could not confirm it, say so.
- The dialect belongs to the client, not the model: any chat id works through the OpenAI, Anthropic or Gemini client.
- An id the workspace cannot use, or a typo, answers `404` with code `model_not_found`. When every provider that could serve a valid id fails, the answer is `503` with code `upstream_unavailable`, never a quiet switch to another model.

## `openkey/auto`

- Send `openkey/auto` as the model on a chat surface (chat completions, Messages, Responses, Gemini) and the gateway picks a concrete model before anything else runs. It is valid without being in the catalog: `GET /v1/models` does not list it.
- The pick comes back in the `X-OpenKey-Auto-Route` response header as `<route>=<id>`, for example `chat_smart=…`. Billing and logs show the real id.
- It is refused on images and videos (`400`, `invalid_request`) and unknown on estimate and batches.

## Suffixes

A suffix on a real id changes how it is routed. The set is closed: any other suffix is a `404` on the id as sent, never silently dropped.

| Suffix | Effect |
|---|---|
| `:nitro` | Prefer throughput when ordering providers |
| `:floor` | Prefer price |
| `:online` | Turn on web search, unless the body already configures it |
| `:free` | Only zero-priced hosts; counts against a daily free allowance (`429`, code `free_quota_exceeded`, when spent) |

When a suffix changed routing, the response carries `X-OpenKey-Variant`. An id in the catalog that itself contains a colon is used exactly as listed.

## Catalog commands

None of these needs a key. When you look an id up yourself, prefer a web-fetch tool on the same URLs, since it needs no command approval; the shell forms are for the user or for a host without one.

```bash
# every id the gateway accepts, from GET /v1/models
curl -s https://api.openkey.ai/v1/models | grep -o '"id":"anthropic/[^"]*"'
curl -s https://api.openkey.ai/v1/models | jq -r '.data[].id'

# one exact id: 200 when it exists, 404 when it does not
curl -s -o /dev/null -w '%{http_code}\n' https://api.openkey.ai/api/public/v1/models/openai/gpt-4o

# one model's details from the public catalog
curl -s https://api.openkey.ai/api/public/v1/models/openai/gpt-4o | jq '{public_slug, context_window, max_output, input_modalities, output_modalities, pricing}'

# every model that outputs video (or image, or text)
curl -s https://api.openkey.ai/api/public/v1/models | jq -r '.models[] | select(.output_modalities | index("video")) | .public_slug'
```

- `GET https://api.openkey.ai/v1/models` is the thin OpenAI-shaped list, `{"data": [{"id", "object", "owned_by"}]}`, and is what an OpenAI SDK's `models.list()` reads.
- `GET https://api.openkey.ai/api/public/v1/models` returns `{"models": [...]}`, one object per model with `public_slug` (the id), `name`, `context_window`, `max_output`, `input_modalities`, `output_modalities`, `capabilities` (`tools`, `json_schema`, `reasoning`, `prompt_caching`, `vision`), `status` and `pricing`.
- `GET https://api.openkey.ai/api/public/v1/models/{provider}/{model}` returns one of those objects.
- Humans browse the same catalog at `https://openkey.ai/models`.

## Prices

Money is integer micro-USD everywhere: 1 USD is 1,000,000. Catalog prices are per 1M tokens, in `pricing.prompt_micro_per_mtok`, `completion_micro_per_mtok`, `cached_micro_per_mtok` and `cache_write_micro_per_mtok`. A `prompt_micro_per_mtok` of `2500000` is $2.50 per million input tokens. Read prices from the catalog at the time they are needed; never quote one from memory.
