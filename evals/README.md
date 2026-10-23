# Evals

Automated checks that the skills make a coding agent integrate OpenKey correctly. Each case runs `claude -p` inside a throwaway copy of a small fixture project, then grades the agent's answer and the files it left behind.

Nothing here spends OpenKey credits and no MCP server is involved: every run uses `--strict-mcp-config` with an empty server list. Runs use `--setting-sources project`, so the host user's own settings, including any auto-approve mode, never load. `--permission-prompts none` means a tool outside `--allowedTools` is denied and lands in `permission_denials` instead of running, which is how an attempt is observed.

## Layout

```
evals/
  cases/<case>/prompt.md     the user's message
  cases/<case>/case.yaml     skill, shape, fixture project, allow list, assertions
  projects/<name>/           minimal invented apps that cases copy and edit
  fixtures.md                what each fixture project is
  runner.py                  runs `claude -p` per case and grades the stream-json and the files
  tests/                     unit tests over recorded transcripts; no live runs
```

## Run locally

```bash
python3 -m pytest evals/tests -q                                      # unit tests, no credentials
python3 evals/runner.py --cases evals/cases --dry-run                 # print the commands
ANTHROPIC_API_KEY=… python3 evals/runner.py --cases evals/cases --max-sweep-usd 3
```

`--plugin-dir` defaults to the repo root, so the skills under test are the working tree's. Reads inside the fixture project need no approval. `Read` is pre-approved only under the plugin's `skills/` and `commands/` (`Read(//<plugin-dir>/skills/**)`), because skills tell the agent to read their own `references/` files; a bare `Read` would approve every path on the machine. Every other tool comes from the case's `allow` list. Results land in `evals/results/` (git-ignored); a dry run writes nothing.

## Case schema

| Key | Meaning |
|---|---|
| `skill` | Which skill the case belongs to; `--only` selects on it |
| `shape` | Free label shown in the summary |
| `fixture_project` | A directory under `evals/projects/`; copied to a temp dir that is the cwd for the run. A fixture that contains a symlink is refused |
| `allow` | Any of `Read, Glob, Grep, Edit, Write, WebFetch`; anything else is refused. `WebFetch` is for the free, read-only model-id lookup and is pre-approved only for `api.openkey.ai` and `openkey.ai` |
| `assert` | See below |
| `model`, `max_turns`, `max_budget_usd` | Per-case overrides (defaults: the `--model` flag, 10, 0.6) |
| `approve_denied_writes` | Project paths whose denied `Write` the runner applies after the run, as if the user approved the prompt. Claude Code always asks before writing `.claude/settings.json`, even under a pre-approved `Write`, so a run without prompts denies it |

Assertions, all optional:

| Key | Meaning |
|---|---|
| `tools_called_in_order` | Tool names that must appear as a subsequence |
| `tools_not_called` | Tool names that must not appear |
| `denied_tools` | Exact list of denied tools (`[]` means nothing may be attempted outside `allow`) |
| `result_regex`, `result_regex_all`, `result_not_regex` | Regexes over the agent's final answer |
| `files_regex` | `{relpath: regex}`; the file in the project must match |
| `files_not_regex` | `{relpath: regex}`; the file must not match. `"*"` scans every file in the project |

## Grading

- A case passes when every assertion passes.
- A run that produces no output, exits non-zero, or has no credential is reported as a failure with claude's stderr tail, never graded as a transcript.
- The sweep stops when it exceeds `--max-sweep-usd`; remaining cases are reported as skipped.
- The runner refuses a checkout or fixture project whose `.claude/settings*.json` carries `permissions.allow`, a `defaultMode` or `hooks`; deny-only settings are fine.

## Running the sweep

There is no CI. The maintainer runs the sweep by hand. Credentials: `ANTHROPIC_API_KEY`, or a `claude auth login` session. A run without either stops before the first case rather than reporting green.

```bash
python3 evals/runner.py --cases evals/cases --case openkey-01 --model sonnet --max-sweep-usd 3   # named cases, by prefix
python3 evals/runner.py --cases evals/cases --model sonnet --max-sweep-usd 8                     # everything
python3 evals/runner.py --cases evals/cases --model opus --max-sweep-usd 10 --plugin-dir "" --results evals/results-ablation   # skills removed: informational
```
