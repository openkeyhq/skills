# Claude Code on OpenKey

Claude Code speaks the Anthropic Messages API. Environment variables point it at OpenKey: the base URL, the token and the model ids.

## Per user: the shell

macOS or Linux, in `~/.zshrc` or `~/.bashrc`, after the line where the user exports `OPENKEY_API_KEY` with their own key:

```bash
export ANTHROPIC_BASE_URL="https://api.openkey.ai"
export ANTHROPIC_AUTH_TOKEN="$OPENKEY_API_KEY"
export ANTHROPIC_MODEL="openkey/auto"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="anthropic/claude-haiku-4.5"
export ANTHROPIC_DEFAULT_SONNET_MODEL="anthropic/claude-sonnet-4.5"
export ANTHROPIC_DEFAULT_OPUS_MODEL="anthropic/claude-opus-4.5"
```

Windows PowerShell. `setx` persists each value for new shells and copies the current value of `OPENKEY_API_KEY`:

```powershell
setx ANTHROPIC_BASE_URL "https://api.openkey.ai"
setx ANTHROPIC_AUTH_TOKEN "$env:OPENKEY_API_KEY"
setx ANTHROPIC_MODEL "openkey/auto"
setx ANTHROPIC_DEFAULT_HAIKU_MODEL "anthropic/claude-haiku-4.5"
setx ANTHROPIC_DEFAULT_SONNET_MODEL "anthropic/claude-sonnet-4.5"
setx ANTHROPIC_DEFAULT_OPUS_MODEL "anthropic/claude-opus-4.5"
```

- Anthropic protocol: bare host, no `/v1`. Claude Code appends `/v1/messages` itself; adding `/v1` produces `/v1/v1/messages`, which fails.
- `ANTHROPIC_AUTH_TOKEN` is the OpenKey key. Claude Code sends it as `Authorization: Bearer`.
- `openkey/auto` lets the gateway pick the model per request. To pin one, use a `provider/model` id confirmed in `https://api.openkey.ai/v1/models`, such as `anthropic/claude-sonnet-4.5`.
- OpenKey resolves only `provider/model` ids. Without the three `ANTHROPIC_DEFAULT_*_MODEL` lines, Claude Code's background tasks, subagents and the `sonnet`/`opus` aliases send bare model names and fail with a `404`. Pick newer ids from `GET https://api.openkey.ai/v1/models`.
- Then run `claude`. Requests show on the Activity page of the OpenKey app within seconds.

## Committed: `.claude/settings.json`

The project half, checked in, so a fresh clone uses OpenKey and is tagged on its first request:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.openkey.ai",
    "ANTHROPIC_MODEL": "openkey/auto",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "anthropic/claude-haiku-4.5",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "anthropic/claude-sonnet-4.5",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "anthropic/claude-opus-4.5",
    "ANTHROPIC_CUSTOM_HEADERS": "X-OpenKey-Tags: project=atlas"
  }
}
```

- `atlas` stands for the repository's directory name, limited to `A-Za-z0-9._:@-` and 64 characters.
- The file has no token. Each developer sets `ANTHROPIC_AUTH_TOKEN="$OPENKEY_API_KEY"` in their own shell, or adds `ANTHROPIC_AUTH_TOKEN` to the `env` block of their own `.claude/settings.local.json`, which they write themselves.
- The file reroutes Claude Code for every teammate who opens the repo. Until a teammate sets `ANTHROPIC_AUTH_TOKEN` from `OPENKEY_API_KEY`, Claude Code sends their own Anthropic credential or login to `api.openkey.ai` and gets `401`. Tell each person to set the token first.
- If `.claude/settings.json` already exists, read it, add these keys to its `env` block and keep everything else.
- Make sure `.gitignore` lists `.claude/settings.local.json`. Read `.gitignore` first and add only the missing line.
- Claude Code asks the user before it writes `.claude/settings.json`, even when edits are pre-approved. If the write is refused, give the user the file's content to save.

## Headers: `ANTHROPIC_CUSTOM_HEADERS`

- The format is `Name: Value`, with several headers separated by newlines. It needs Claude Code v2.1.227 or later.
- Set it in the shell, in the `env` block of `.claude/settings.json` (committed), or in `.claude/settings.local.json` (personal).
- It is one variable. Once the committed `.claude/settings.json` sets it, a shell value is dropped, and a value in `.claude/settings.local.json` takes precedence over the committed one. So a developer adds `X-OpenKey-User` in `.claude/settings.local.json` and repeats the tags line there:

```json
{
  "env": {
    "ANTHROPIC_CUSTOM_HEADERS": "X-OpenKey-Tags: project=atlas\nX-OpenKey-User: dev@example.com"
  }
}
```

**Do not commit a personal identifier.** `X-OpenKey-Tags: project=…` is a property of the repository and belongs in a shared file. `X-OpenKey-User` is a property of the person and belongs in a git-ignored local settings file, or in their shell when no committed file sets the header. A committed end-user id attributes the whole team to whoever set it up.
