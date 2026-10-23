# Claude Code on OpenKey

Claude Code speaks the Anthropic Messages API. Settings point it at OpenKey: the base URL and model ids in the `env` block, and the key through `apiKeyHelper`.

## Per user: `~/.claude/settings.json`

The user settings file applies to every project on the machine: `~/.claude/settings.json` on macOS and Linux, `%USERPROFILE%\.claude\settings.json` on Windows. If it exists, read it and merge these keys in; keep everything else.

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

- Why not shell-profile exports or `setx`: they make `ANTHROPIC_BASE_URL` and `ANTHROPIC_AUTH_TOKEN` global, so every Anthropic-SDK program the user starts is rerouted. Each sends its own Anthropic key to OpenKey, and one that sets Anthropic's base URL itself sends the OpenKey key to Anthropic. `env` values here reach only Claude Code and the commands it runs.
- `apiKeyHelper` is a top-level key, not part of `env`. Claude Code runs the command and sends its output as both `X-Api-Key` and `Authorization: Bearer`. The file holds no key: the user exports `OPENKEY_API_KEY` with their own key in their shell profile. With the variable unset, the helper prints nothing and Claude Code stops with `apiKeyHelper script is failing`.
- `ANTHROPIC_AUTH_TOKEN` and `ANTHROPIC_API_KEY` outrank `apiKeyHelper`. If the user's shell exports either one, Claude Code sends that value to OpenKey instead; unset both in the shell that starts `claude`.
- Anthropic protocol: bare host, no `/v1`. Claude Code appends `/v1/messages` itself; adding `/v1` produces `/v1/v1/messages`, which fails.
- `openkey/auto` lets the gateway pick the model per request. To pin one, use a `provider/model` id confirmed in `https://api.openkey.ai/v1/models`, such as `anthropic/claude-sonnet-4.5`.
- OpenKey resolves only `provider/model` ids. Without the three `ANTHROPIC_DEFAULT_*_MODEL` lines, Claude Code's background tasks, subagents and the `sonnet`/`opus` aliases send bare model names and fail with a `404`. Pick newer ids from `GET https://api.openkey.ai/v1/models`.
- Then run `claude`. Requests show on the Activity page of the OpenKey app within seconds.

### Windows

Claude Code runs `apiKeyHelper` with `cmd` on Windows, and `cmd` has no `printenv`. Use PowerShell to read the variable instead; with `OPENKEY_API_KEY` unset it prints nothing, so the helper still fails closed. Unverified: OpenKey has not run this form on Windows; say so to the user.

```json
{
  "apiKeyHelper": "powershell -NoProfile -Command $env:OPENKEY_API_KEY"
}
```

The user sets `OPENKEY_API_KEY` as a user environment variable themselves (System Properties → Environment Variables) and opens a new terminal.

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
  },
  "apiKeyHelper": "printenv OPENKEY_API_KEY"
}
```

- `atlas` stands for the repository's directory name, limited to `A-Za-z0-9._:@-` and 64 characters.
- The file has no key: `apiKeyHelper` reads each developer's own `OPENKEY_API_KEY`.
- The file reroutes Claude Code for every teammate who opens the repo. `apiKeyHelper` outranks the claude.ai login, so a teammate without `OPENKEY_API_KEY` gets `apiKeyHelper script is failing` instead of sending their subscription token to OpenKey.
- The gap that remains: `ANTHROPIC_AUTH_TOKEN` and `ANTHROPIC_API_KEY` outrank the helper, so a teammate who exports either sends it to `api.openkey.ai` until they unset it. On Windows the `printenv` helper always fails, which is closed but unusable, until the teammate puts the PowerShell form above in their own `.claude/settings.local.json`, which outranks the committed file.
- Propose a commit message with a one-line notice for teammates: export `OPENKEY_API_KEY`, and unset `ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN` before running `claude` in this repo.
- If `.claude/settings.json` already exists, read it, add these keys to it and keep everything else.
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
