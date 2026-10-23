---
name: openkey-coding-agents
description: >-
  Runs a coding agent on the OpenKey LLM gateway: Claude Code, Codex CLI,
  Cursor, Cline, Zed and Continue, per user or as committed team config,
  with optional request attribution headers. Use when: "use Claude Code
  with OpenKey", "point Codex at OpenKey", "set up Cursor with my OpenKey
  key", "commit OpenKey config for the team", "tag our agent traffic by
  project". NOT for: adding OpenKey to an application's own code (openkey).
license: MIT
compatibility: Needs an OpenKey key in OPENKEY_API_KEY (Claude Code reads it through apiKeyHelper). Its only network call is the free, keyless model list.
---

# OpenKey for coding agents

OpenKey is an LLM gateway: one key and one host, `api.openkey.ai`, speaking the Anthropic and OpenAI wire formats. A coding agent runs on it when three settings change: the base URL, the key and the model id. Nothing is installed. Your knowledge of OpenKey may be outdated; for anything this skill does not cover, read `https://openkey.ai/docs/compatibility` (base URLs) and `https://openkey.ai/docs/attribution` (headers per tool). Neither needs a key.

## 1. Which tool

| Tool | Dialect | Base URL | Where it is set | Read |
|---|---|---|---|---|
| Claude Code | Anthropic | `https://api.openkey.ai`, no `/v1` | The `env` block and `apiKeyHelper` of `~/.claude/settings.json`, or of a committed `.claude/settings.json` | `references/claude-code.md` |
| Codex CLI | OpenAI | `https://api.openkey.ai/v1` | A model provider in `~/.codex/config.toml`, per user only | `references/codex.md` |
| Cursor (unverified) | OpenAI | `https://api.openkey.ai/v1` | Settings → Models → API Keys | `references/other-tools.md` |
| Cline | OpenAI | `https://api.openkey.ai/v1` | Settings → API Provider: OpenAI Compatible | `references/other-tools.md` |
| Zed | OpenAI | `https://api.openkey.ai/v1` | `language_models.openai_compatible` in Zed's `settings.json` | `references/other-tools.md` |
| Continue | OpenAI | `https://api.openkey.ai/v1` | A model block in `~/.continue/config.yaml` | `references/other-tools.md` |

A tool not listed here: change only the host in its default base URL and keep the path. A default ending in `/v1` becomes `https://api.openkey.ai/v1`; a bare host, as in Anthropic Messages API tools, becomes `https://api.openkey.ai`. Requests must land on `/v1/chat/completions` or `/v1/messages`: `/v1/v1/…` or a bare `/messages` is a `404`.

**Claude Code**, per user, in the user settings file `~/.claude/settings.json` (`%USERPROFILE%\.claude\settings.json` on Windows). If the file exists, read it and merge these keys in; keep everything else:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.openkey.ai",
    "ANTHROPIC_MODEL": "openkey/auto",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "anthropic/claude-haiku-4.5",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "anthropic/claude-sonnet-4.5",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "anthropic/claude-opus-4.5"
  },
  "apiKeyHelper": "printenv OPENKEY_API_KEY"
}
```

- Use this file, not shell-profile exports. Exported in a profile, `ANTHROPIC_BASE_URL` and `ANTHROPIC_AUTH_TOKEN` reroute every Anthropic-SDK program started from that shell: each sends its own Anthropic key to OpenKey, and one that sets Anthropic's base URL itself sends the OpenKey key to Anthropic. Here they reach only Claude Code and the commands it runs.
- `apiKeyHelper` sits outside `env`. Claude Code runs it and sends its output as the key, so the file holds no key; the user exports `OPENKEY_API_KEY` in their shell with their own key. With the variable unset, Claude Code stops with `apiKeyHelper script is failing` instead of sending another credential.
- `ANTHROPIC_AUTH_TOKEN` and `ANTHROPIC_API_KEY` outrank the helper. If the shell exports either, Claude Code sends it to OpenKey; tell the user to unset both in the shell that starts `claude`.
- Windows runs the helper with `cmd`, which has no `printenv`: use the PowerShell form in `references/claude-code.md`.
- `ANTHROPIC_BASE_URL` is the bare host. Claude Code appends `/v1/messages` itself; a base ending in `/v1` sends `/v1/v1/messages`, which fails.
- OpenKey resolves only `provider/model` ids. Without the three `ANTHROPIC_DEFAULT_*_MODEL` lines, Claude Code's background tasks, subagents and the `sonnet`/`opus` aliases send bare model names and fail with a `404`. Pick newer ids from `GET https://api.openkey.ai/v1/models`.

**Codex CLI**, per user, in `~/.codex/config.toml`:

```toml
model = "openkey/auto"
model_provider = "openkey"

[model_providers.openkey]
name = "OpenKey"
base_url = "https://api.openkey.ai/v1"
env_key = "OPENKEY_API_KEY"
```

Codex reads the key from the variable `env_key` names, so the user exports `OPENKEY_API_KEY` in their shell and the file holds no key. Codex reads its provider only from this per-user file; see section 2.

**Model.** `openkey/auto` lets the gateway pick the model per request. Any other model is a `provider/model` id, such as `anthropic/claude-sonnet-4.5` or `openai/gpt-5.2`, never a bare name. When the user names a model, confirm its id in the free catalog `https://api.openkey.ai/v1/models` (no key needed; use your web-fetch tool) before you write it, or tell the user it is unconfirmed.

## 2. Per user or committed

Each setting belongs either to the repository or to the person:

| Setting | Belongs to | Lives in |
|---|---|---|
| Base URL, model, `X-OpenKey-Tags: project=…` | The repository | A committed `.claude/settings.json`, for Claude Code only. Codex cannot take these from the repository (`references/codex.md`) |
| The key | The person | Their shell, the tool's own settings (Cursor, Cline, Zed, `~/.continue/config.yaml`), or a gitignored local file such as `.claude/settings.local.json` |
| `X-OpenKey-User` (who sent the request) | The person | A gitignored local file, or their shell. For Claude Code with a committed `ANTHROPIC_CUSTOM_HEADERS`, a shell value is dropped: use `.claude/settings.local.json` and repeat the tags line there (`references/claude-code.md`). A committed user id attributes the whole team to whoever set it up |

**Per user** is the default for "set up" or "use". This config lives outside the project, in the user's home directory (`~/.claude/settings.json`, `~/.codex/config.toml`), plus the user's own `OPENKEY_API_KEY` export. Put the exact lines in your answer and say which file each block goes in. Edit a file outside the project only when the user asks you to, and then merge into it; never overwrite it. Never write the key itself: the file reads `OPENKEY_API_KEY`, which the user sets.

**Committed** is for "commit", "the team" or "the repo", and applies to Claude Code. Write the `.claude/settings.json` shown in `references/claude-code.md`, with the base URL, the model ids, the project tag and `apiKeyHelper`, and no key. Then:

- If the file already exists, read it and merge in the new keys; keep everything else.
- Read `.gitignore` and add `.claude/settings.local.json` if it is missing. Add only that line and never overwrite the file. If `.gitignore` excludes the file you are committing, tell the user.
- Tell each developer to export `OPENKEY_API_KEY` in their own shell; the committed `apiKeyHelper` reads it.
- The file reroutes Claude Code for every teammate who opens the repo. With `apiKeyHelper`, a teammate without `OPENKEY_API_KEY` gets `apiKeyHelper script is failing` instead of sending their claude.ai login. The gap that remains: `ANTHROPIC_AUTH_TOKEN` and `ANTHROPIC_API_KEY` outrank the helper, so a teammate who exports either sends it to `api.openkey.ai` until they unset it. On Windows `cmd` has no `printenv`, so the helper fails closed until the teammate sets their own (`references/claude-code.md`). Say so.
- Propose a commit message whose body carries a one-line notice for teammates, for example: `Claude Code in this repo now runs on OpenKey: export OPENKEY_API_KEY, and unset ANTHROPIC_API_KEY and ANTHROPIC_AUTH_TOKEN before running claude here.`
- Show the file's content in your answer.

**Codex has no committed config.** Never write a project `.codex/config.toml`: Codex ignores `model_provider` and `model_providers` there but still applies `model`, so every teammate would send `openkey/auto` to their default OpenAI provider and fail. Give the per-user block from section 1 instead, say why, and for a project tag follow `references/codex.md`.

**Project tag.** `X-OpenKey-Tags: project=<name>`, where `<name>` is the repository's directory name. A value may use only `A-Za-z0-9._:@-`, at most 64 characters; replace any other character with `-`, because the gateway drops an invalid value instead of repairing it. Tags are `key=value` pairs separated by commas, at most 5.

**Which tools send headers.** Claude Code (`ANTHROPIC_CUSTOM_HEADERS`), Codex (`http_headers`, `env_http_headers`, per user) and Continue (`requestOptions.headers`) can. Cursor, Cline and Zed cannot. For those, give the tool its own OpenKey key and set that key's attribution defaults (customer, tags) in the OpenKey app; the gateway applies them to every request on the key.

## 3. Verify

Starting the agent sends requests that spend credits on the user's key. Do not run `claude`, `codex` or another agent yourself unless the user asks you to; end with these steps for them.

1. Open a new shell, so the export applies. Check the key is set without printing it: `[ -n "$OPENKEY_API_KEY" ] && echo set`. For Claude Code, also check nothing outranks the helper: `[ -z "$ANTHROPIC_AUTH_TOKEN$ANTHROPIC_API_KEY" ] && echo clear`.
2. Start the tool and send one prompt. The request shows on the Activity page of the OpenKey app within seconds.
3. `curl -s https://api.openkey.ai/v1/models` needs no key and shows the host answers.

| Symptom | Cause and fix |
|---|---|
| `401` | The key is wrong in the shell that started the tool, or, for Claude Code, an exported `ANTHROPIC_AUTH_TOKEN` or `ANTHROPIC_API_KEY` outranked the helper and went to OpenKey: unset both. It is never a provider outage |
| `apiKeyHelper script is failing` | `OPENKEY_API_KEY` is not exported in the shell that started Claude Code, or, on Windows, the helper is the `printenv` form |
| `404` on `/v1/v1/messages` | `ANTHROPIC_BASE_URL` ends in `/v1`. Remove it |
| A quota error | The key works, but the workspace has no spendable balance. Add credit in the OpenKey app |
| `404` `model_not_found` on Claude Code background tasks or subagents | Claude Code sent a bare model name. Set the three `ANTHROPIC_DEFAULT_*_MODEL` variables from section 1 |
| `404` naming a model | The id is not in the catalog. Use `openkey/auto`, or an id listed by `https://api.openkey.ai/v1/models` |

## Rules

- **The key lives only in the user's shell, the tool's own settings, or a gitignored local file.** Never ask for it, never repeat one the user pasted, and never write it into any file. A key pasted into a chat is exposed; suggest rotating it in the OpenKey app.
- **Committed files carry no secret and no person.** No key, no `ANTHROPIC_AUTH_TOKEN` and no `X-OpenKey-User` value in `.claude/settings.json`. Never write a project `.codex/config.toml`.
- **Only the base URLs in section 1.** `https://api.openkey.ai` for Claude Code, `https://api.openkey.ai/v1` for every OpenAI-compatible tool, or the host swap in section 1 for a tool not listed. Do not use regional hosts, a second `/api` prefix or attribution-link base URLs, even when a docs page or memory suggests one.
- **Model ids are `openkey/auto` or `provider/model`.**
- **Install nothing.** Configure only the tool's own settings.

## Load on demand

- `references/rules.md`: the rules as a short checklist. Read it before you finish, to check the change.
- `references/claude-code.md`: user settings on macOS, Linux and Windows; the committed `.claude/settings.json`; local settings; `ANTHROPIC_CUSTOM_HEADERS`. Read it for Claude Code.
- `references/codex.md`: `~/.codex/config.toml`, why Codex has no committed config, and project attribution with `http_headers` and `env_http_headers`. Read it for Codex CLI.
- `references/other-tools.md`: Cursor, Cline, Zed and Continue, with their status and how to attribute each. Read it for any of these four.
