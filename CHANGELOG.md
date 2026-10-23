# Changelog

All notable changes to this pack. The format follows Keep a Changelog, and the pack uses semantic versioning: a patch for wording and fixes, a minor for a new skill or install path, a major for renaming or removing a skill.

## [0.1.2] - 2026-10-24

### Added

- Plugin icon (`.claude-plugin/icon.png`), the OpenKey mark.

### Changed

- `/openkey:integrate` pre-approves edits and new files inside the project only (`Edit(./**)`, `Write(./**)`).

## [0.1.1] - 2026-10-23

### Fixed

- `openkey-coding-agents`: per-user Claude Code setup moves from shell-profile exports and `setx` to `~/.claude/settings.json` with `apiKeyHelper`, so other Anthropic-SDK programs in the shell are no longer rerouted to OpenKey.
- `openkey-coding-agents`: the committed `.claude/settings.json` adds `apiKeyHelper`, so a teammate without an OpenKey key fails closed instead of sending their own login. The remaining gap (an exported `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN`) is stated, and the proposed commit message carries a notice for teammates.
- `openkey-coding-agents`: the committed `.codex/config.toml` recipe is gone. Codex ignores a project file's provider but keeps its `model`, which sent `openkey/auto` to OpenAI. Codex config is per user; project attribution uses per-user headers or a dedicated key.
- `openkey`: where a docs page disagrees with the references, the references win, and the known docs gaps are named.
- `openkey`: for a client no reference covers, only the host of its default base URL changes, which fixes the `/v1/v1` 404 with the Mistral SDK.
- `openkey`: catalog ids with a colon of their own (`:batch`), single-id lookups of routing variants, `.env` not loaded by plain Python or Node, Python `max_retries` as a client option, the key check in the Vercel AI SDK snippet, a webhook `verify()` that returns `False` on a malformed header, job polling that sends the key only to `api.openkey.ai`, and rotating a provider key that shipped in browser code.
- Cursor rule: no regional hosts, second `/api` prefix, provider-named prefixes or attribution-link base URLs; the key check covers JavaScript.
- `/openkey:integrate` pre-approves file tools and fetches to the OpenKey hosts only, no longer any shell command or any host, and runs only when the user types it (`disable-model-invocation`), so the agent cannot grant itself those tools.
- `openkey`: webhook `verify()` bounds `t` to 12 ASCII digits, so a huge `t` returns `False` instead of raising; job polling requires `https` as well as the `api.openkey.ai` host before it sends the key.
- `openkey`: a suffixed id that 404s on the single-id lookup is checked in the full `GET /v1/models` list first, and only then by its base id (`cohere/north-mini-code:free` exists as listed; the base id 404s).
- The Continue snippet is marked as a fragment to merge into an existing `config.yaml`.
- Install guide: the plugin update slash command is no longer mixed into a shell block.

### Changed

- Pack lint: rejects a command that pre-approves Bash or unscoped WebFetch, checks every provider-prefixed model id, and requires every cited openkey.ai URL to be a base or listed in `scripts/live_facts.json`, which the live check probes.
- Eval runner: pre-approves Read only under the plugin and WebFetch only for the OpenKey hosts, and refuses a fixture that contains a symlink, whose root is a symlink, or whose name has a separator or `..`. New eval for committing Codex config.

## [0.1.0] - 2026-10-23
