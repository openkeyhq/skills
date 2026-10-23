# Codex CLI on OpenKey

Codex speaks the OpenAI API. OpenKey is added as a model provider in `config.toml`, and Codex reads the key from the environment variable that `env_key` names.

## Per user: `~/.codex/config.toml`

```toml
model = "openkey/auto"
model_provider = "openkey"

[model_providers.openkey]
name = "OpenKey"
base_url = "https://api.openkey.ai/v1"
env_key = "OPENKEY_API_KEY"
```

Then, in the user's shell profile, with their own key in place of the placeholder:

```bash
export OPENKEY_API_KEY="sk-ok-…"
```

- OpenAI dialect: `base_url` includes `/v1`.
- If `~/.codex/config.toml` already exists, read it and keep its other settings. TOML allows each key once, so replace an existing top-level `model` or `model_provider` rather than adding a second one. Top-level keys go above the first `[table]` header; below it they belong to that table.
- `openkey/auto` lets the gateway pick the model per request. To pin one, use a `provider/model` id confirmed in `https://api.openkey.ai/v1/models`, such as `openai/gpt-5.2`.
- Save the file, export the key, then run `codex`. Requests show on the Activity page of the OpenKey app within seconds.

## No committed config

Codex ignores `model_provider` and `[model_providers.*]` in a project-level `.codex/config.toml`, and says so in a warning: a project may not choose where a user's credentials go. It still applies the project's `model`. A committed file with `model = "openkey/auto"` therefore sends that id to each teammate's default OpenAI provider, which rejects it.

- Never write a project `.codex/config.toml` that sets `model` or a provider.
- When the user asks to commit Codex config for the team, give each developer the per-user block above, for their own `~/.codex/config.toml`, and say why.

## Project attribution

Codex cannot carry a project tag in the repository. Two ways to attribute:

- Each developer adds headers to the provider table in their own `~/.codex/config.toml`. The headers belong to `[model_providers.openkey]`, not to the top level:

```toml
[model_providers.openkey]
name = "OpenKey"
base_url = "https://api.openkey.ai/v1"
env_key = "OPENKEY_API_KEY"
http_headers = { "X-OpenKey-Tags" = "project=atlas" }
env_http_headers = { "X-OpenKey-User" = "OPENKEY_END_USER" }
```

  `http_headers` are static, so this tag applies to every repository the developer runs Codex in; `atlas` stands for the project name, limited to `A-Za-z0-9._:@-` and 64 characters. `env_http_headers` maps a header to an environment variable instead, such as `{ "X-OpenKey-Tags" = "OPENKEY_TAGS", "X-OpenKey-User" = "OPENKEY_END_USER" }`, so the developer can set the tag per shell and their own user id.
- Or give Codex its own OpenKey key and set that key's attribution defaults (customer, tags) in the OpenKey app; the gateway applies them to every request on the key.

If neither fits, tell the user that Codex cannot carry a repository-level tag.

## Check

- `[ -n "$OPENKEY_API_KEY" ] && echo set` in the shell that starts `codex` confirms the key without printing it.
- A `401` means `OPENKEY_API_KEY` is missing or wrong in that shell.
