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

## Committed: `.codex/config.toml`

OpenAI's Codex docs also list a project-level `.codex/config.toml`. The provider block goes there, checked in, with the attribution headers:

```toml
model = "openkey/auto"
model_provider = "openkey"

[model_providers.openkey]
name = "OpenKey"
base_url = "https://api.openkey.ai/v1"
env_key = "OPENKEY_API_KEY"
http_headers = { "X-OpenKey-Tags" = "project=atlas" }
env_http_headers = { "X-OpenKey-User" = "OPENKEY_END_USER" }
```

- `http_headers` are static and the same for everyone, which suits the project tag. `atlas` stands for the repository's directory name, limited to `A-Za-z0-9._:@-` and 64 characters.
- `env_http_headers` maps a header to an environment variable. Each developer exports `OPENKEY_END_USER` with their own id in their shell. The committed file names the variable, never a person.
- The file has no key: `env_key` names the variable, and each developer exports `OPENKEY_API_KEY` in their own shell.
- If `.gitignore` excludes `.codex/`, the file will not be committed; tell the user.

## Check

- `[ -n "$OPENKEY_API_KEY" ] && echo set` in the shell that starts `codex` confirms the key without printing it.
- A `401` means `OPENKEY_API_KEY` is missing or wrong in that shell.
