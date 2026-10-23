---
name: openkey
description: >-
  Integrates the OpenKey LLM gateway into a project's code: one OpenKey key
  and base URL in place of direct OpenAI, Anthropic or Gemini calls, through
  the SDK the project already uses or plain HTTP. Picks model ids, reads
  errors and X-OpenKey headers, and keeps the key in an environment
  variable. Use when: "use OpenKey in this app", "switch our OpenAI calls to
  OpenKey", "call Claude through OpenKey from Python", "which OpenKey model
  id do I use", "what does this OpenKey error mean", "add an LLM call with
  OpenKey". NOT for: running Claude Code, Codex, Cursor or another coding
  agent on OpenKey (openkey-coding-agents).
license: MIT
compatibility: Needs network access to api.openkey.ai and an OpenKey key in OPENKEY_API_KEY to run the code it writes; gives advice without either.
---

# OpenKey

OpenKey is an LLM gateway: one key and one host, `api.openkey.ai`, in front of many model labs, speaking the OpenAI, Anthropic and Gemini wire formats. Putting it into a project means changing the base URL and the key of the client the project already uses, and naming models `provider/model`. Nothing new is installed. Your knowledge of OpenKey may be outdated. Prefer retrieval over pre-training.

## Retrieval sources

The model ids and URLs in this skill are re-checked against production for every release. For anything this skill and its references do not cover, read these first; none of them needs a key.

| Source | How | Use for |
|---|---|---|
| `https://openkey.ai/llms.txt` | fetch | Index of the docs and feature pages |
| Docs pages | `https://openkey.ai/docs/<page>`: `quickstart`, `compatibility`, `authentication`, `chat`, `models`, `routing`, `headers`, `errors`, `estimate`, `media`, `jobs`, `webhooks` | Dialects, headers, error codes, media and async jobs |
| `GET https://api.openkey.ai/v1/models` | `curl -s https://api.openkey.ai/v1/models` | Every model id the gateway accepts right now |
| `GET https://api.openkey.ai/api/public/v1/models` | `curl -s https://api.openkey.ai/api/public/v1/models` | Names, context windows, modalities, prices (integer micro-USD per 1M tokens) |
| `https://openkey.ai/llms-full.txt` then the model's `llms.txt` | fetch `llms-full.txt`, find the line for the model id, take that line's model page URL and append `/llms.txt` (drop a leading `~`, write `:` as `-x-colon-x-`), e.g. `https://openkey.ai/models/anthropic/claude-haiku-4.5/llms.txt` | One model's contract: price, context, parameters, examples. Do not build the URL from a live id: files exist only for ids with a line in `llms-full.txt`, and aliases such as `anthropic/claude-haiku-4-5` have none (404). For those, use the catalog JSON above |
| `https://openkey.ai/openapi/openkey.yaml` | fetch | Request and response schemas for every route |

Where a docs page disagrees with these references, follow the references: they record the wire as observed in production, and the docs have known gaps (`/v1/messages` errors carry no `code`, `GET /v1/models` needs no key, `X-OpenKey-Request-Id` is missing on some job-route 401s). Where either disagrees with a live response, trust the response.

## 1. Find what the project calls

Search the code for the LLM client before changing anything: imports of `openai`, `anthropic`, `@anthropic-ai/sdk`, `google.genai`, `@google/genai`, `ai` or `@ai-sdk/*`, `langchain`, and HTTP calls to `api.openai.com`, `api.anthropic.com` or `generativelanguage.googleapis.com`. Keep the client and the call shapes the project already has; only the client's configuration and the model ids change.

| Client found | Read |
|---|---|
| OpenAI SDK (`openai` for Python or Node, `openai-go`), or HTTP to `api.openai.com` | `references/openai-sdk.md` |
| Anthropic SDK (`anthropic`, `@anthropic-ai/sdk`), or HTTP to `api.anthropic.com` | `references/anthropic-sdk.md` |
| Gemini: HTTP to `generativelanguage.googleapis.com`, or a Google Gen AI SDK | `references/gemini.md` |
| Vercel AI SDK (`ai`, `@ai-sdk/*`) or LangChain | `references/frameworks.md` |
| Any other library or tool with a base URL or API base setting | `references/frameworks.md`, last section |
| No LLM client yet | The OpenAI SDK in the project's language: `references/openai-sdk.md` |

If the call runs in browser code (a `"use client"` component, `dangerouslyAllowBrowser`, a key in a `NEXT_PUBLIC_` or `VITE_` variable), move it to the server first; see section 5. A provider key that already shipped in such a variable is public: tell the user to rotate it at the provider.

## 2. Swap the base URL and key

| Client dialect | Base URL | Key header | Paths |
|---|---|---|---|
| OpenAI | `https://api.openkey.ai/v1` | `Authorization: Bearer $OPENKEY_API_KEY` | `/chat/completions`, `/responses`, `/embeddings`, `/images/generations` under the base |
| Anthropic | `https://api.openkey.ai` | `x-api-key: $OPENKEY_API_KEY` | The SDK appends `/v1/messages`. A base ending in `/v1` sends `/v1/v1/messages`, a 404 |
| Gemini | `https://api.openkey.ai` | `x-goog-api-key: $OPENKEY_API_KEY` | `/v1beta/models/{model}:generateContent`, where `{model}` is the full OpenKey id |

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://api.openkey.ai/v1",
    api_key=os.environ["OPENKEY_API_KEY"],
)
```

```ts
import OpenAI from "openai";

const apiKey = process.env.OPENKEY_API_KEY;
if (!apiKey) throw new Error("OPENKEY_API_KEY is not set");

const client = new OpenAI({
  baseURL: "https://api.openkey.ai/v1",
  apiKey,
});
```

```python
import os
from anthropic import Anthropic

client = Anthropic(
    base_url="https://api.openkey.ai",
    api_key=os.environ["OPENKEY_API_KEY"],
)
```

- Write the base URL as a literal where the client is built, as above. If the project already reads base URLs from its own config, put the OpenKey URL there instead.
- Read the key from `OPENKEY_API_KEY` where the client is built, in place of the provider key the client used (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`).
- In TypeScript and JavaScript, check the variable before building the client, as above: given an undefined `apiKey`, the OpenAI and Anthropic Node SDKs fall back to `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` and would send the provider key to OpenKey.
- Add `OPENKEY_API_KEY=` with no value to `.env.example` (create it if missing) and make sure `.env` is in `.gitignore`. Read an existing `.gitignore` or `.env.example` first and add only the missing line; never overwrite either.
- Add no dependency: the SDK the project already has is the integration. The one exception is the provider package `references/frameworks.md` names for a framework; say so when you add it.

## 3. Pick the model id

- Ids are `provider/model`, lab first: `openai/gpt-4o`, `anthropic/claude-sonnet-4.5`, `google/gemini-2.5-flash`, `deepseek/deepseek-chat`. A bare name from the user or the code (`gpt-4o`, `claude-sonnet-4.5`) becomes `<lab>/<name>` once you have confirmed it.
- Lab prefixes often differ from brand names: Llama is `meta-llama/`, Grok is `x-ai/`, Mistral is `mistralai/`. Versions may be spelled with a dot or a dash, and ids starting with `~` are aliases that always point at a family's latest model (`~openai/gpt-latest`). Never guess a prefix or a spelling.
- **Confirm every id before you write it.** The lookup is free, read-only and needs no key, so do it without asking. Use your web-fetch tool, not a shell; Claude Code may ask once per domain, and `/openkey:integrate` pre-approves the two OpenKey hosts. If your host lists that tool as deferred, load it first (in Claude Code, `WebFetch` through tool search). Fetch `https://api.openkey.ai/api/public/v1/models/<provider>/<model>` for one exact id (`200` means it exists, `404` that it does not), or `https://api.openkey.ai/v1/models` for the full list when you need the right spelling. If a suffixed id returns `404` on the single-id lookup, check the exact id in the full `GET https://api.openkey.ai/v1/models` list; only if it is absent there, check the base id. Only a host with no web-fetch tool uses `curl -s https://api.openkey.ai/v1/models | grep -o '"id":"anthropic/claude-sonnet[^"]*"'`.
- If you could not confirm an id, write the closest match, tell the user plainly that it is unconfirmed, and give them the command above.
- The client's dialect and the model's lab are independent: an OpenAI-SDK project calls `anthropic/claude-sonnet-4.5` by changing the string, not the SDK.
- Keep the model the project used, as its OpenKey id, unless the user names another.
- `openkey/auto` lets the gateway pick the model, on chat surfaces only; it is not in the `/v1/models` list. The pick comes back in the `X-OpenKey-Auto-Route` response header.
- Suffixes `:nitro`, `:floor`, `:online` and `:free` are a closed set of routing variants; any other suffix is a 404 unless the catalog lists the id with it. The full `GET /v1/models` list also carries ids with a colon of their own, such as the `:batch` ids: use those exactly as listed.
- Grammar, the catalog and prices: `references/models.md`.

## 4. Verify

Running the changed code spends credits on the user's key, so run it only when the user asked you to run or test it; otherwise finish the edit and end with the commands for them to run. The model-id lookup in section 3 spends nothing and is not covered by this rule.

- With `OPENKEY_API_KEY` set and the user's go-ahead: run the changed code path once and confirm a model answer comes back.
- Without a key: tell the user to export `OPENKEY_API_KEY` and run the code. Plain Python and Node do not read `.env`; the gitignored `.env` works only where the project already loads it (python-dotenv, `node --env-file=.env`, or a framework such as Next.js). `curl -s https://api.openkey.ai/v1/models` shows the host answers.
- A `401` means the OpenKey key is missing or wrong, never a provider outage. Other errors: `references/errors.md`.

## 5. Rules for every change

- **The key lives only in the environment.** Code reads `OPENKEY_API_KEY`. Never ask for the key, never repeat one the user pasted, and never write one into any file, `.env` included: the user exports it, or puts it in `.env` when the project loads one. A key pasted into a chat is exposed; suggest rotating it in the OpenKey app.
- **No key in browser code.** CORS blocks the `X-OpenKey-*` headers and a key in a client bundle is public. Move the call into a server route or server action that reads `OPENKEY_API_KEY`, and have the page call that route. Tell the user to rotate any provider key that already shipped in a `NEXT_PUBLIC_` or `VITE_` variable.
- **No OpenKey SDK install.** The OpenKey SDKs are not published to any registry, and a package with a similar name belongs to someone else. Use the SDK the project already has, or plain HTTP with `requests`, `httpx`, `fetch` or `curl`.
- **Only the hosts and paths in section 2.** `https://api.openkey.ai`, with `/v1`, `/v1/messages` or `/v1beta/models`. Do not use regional hosts, a second `/api` prefix, provider-named path prefixes or attribution-link base URLs, even when a docs page or memory suggests one.
- **Tolerate unknown `X-OpenKey-Warning` codes.** The header is a comma-separated list with open-ended codes; log a code you do not know, never fail on it.

## Load on demand

- `references/rules.md`: section 5 as a short checklist. Read it before you finish, to check the change.
- `references/openai-sdk.md`: OpenAI SDK chat in Python, TypeScript, Go and curl; streaming; embeddings; the Responses API. Read it when the project uses the OpenAI SDK or has no client yet.
- `references/anthropic-sdk.md`: Anthropic SDK in Python and TypeScript, curl, and the Anthropic error shape. Read it when the project uses the Anthropic SDK.
- `references/gemini.md`: the Gemini dialect over curl and Python `requests`. Read it when the project calls Gemini.
- `references/frameworks.md`: Vercel AI SDK, LangChain, and any other OpenAI-compatible client. Read it when the project uses a framework or a client no other reference covers.
- `references/models.md`: id grammar, `openkey/auto`, suffixes, catalog commands, prices. Read it when choosing or checking a model id, or reading prices.
- `references/headers.md`: attribution headers, usage disclosure, and the response headers (request id, warnings, budgets). Read it when tagging requests by customer, user or project, or reading what a response reports.
- `references/errors.md`: the error envelope, the seven types, retry rules, in-stream errors. Read it when handling or explaining an OpenKey error.
- `references/media-jobs.md`: images, videos, batches and webhooks. Read it when the project generates images or video, or runs batch jobs.
