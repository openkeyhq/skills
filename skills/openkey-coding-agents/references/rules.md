# OpenKey coding-agent rules

The skill's rules as a checklist, so they travel with any single file of it.

- The key lives in the user's shell as `OPENKEY_API_KEY`, in the tool's own settings, or in a gitignored local file. Never ask for it, repeat it or write it into any file. Suggest rotating a pasted key in the OpenKey app.
- Claude Code reads the key as `ANTHROPIC_AUTH_TOKEN="$OPENKEY_API_KEY"`; Codex through `env_key = "OPENKEY_API_KEY"`.
- Committed files (`.claude/settings.json`, `.codex/config.toml`) carry the base URL, the model and `X-OpenKey-Tags: project=…`. They never carry a key, `ANTHROPIC_AUTH_TOKEN` or an `X-OpenKey-User` value; a Codex `env_http_headers` mapping to a variable name is fine.
- `.gitignore` lists `.claude/settings.local.json`. Read it first and add only missing lines; never overwrite it.
- Base URLs: Claude Code `https://api.openkey.ai`, with no `/v1`; Codex, Cursor, Cline, Zed and Continue `https://api.openkey.ai/v1`. No other host or path prefix, and no attribution link as a base URL.
- Model ids are `openkey/auto`, or a `provider/model` id confirmed in `https://api.openkey.ai/v1/models`. Claude Code also gets `ANTHROPIC_DEFAULT_HAIKU_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL` and `ANTHROPIC_DEFAULT_OPUS_MODEL` set to such ids.
- Per-user config outside the project goes in the answer as exact lines. Edit such a file only when the user asks.
- Start the agent only when the user asks: it spends their credits.
- Install nothing. Configure only the tool's own settings.
