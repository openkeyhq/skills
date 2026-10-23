# Installing OpenKey skills

The pack is skills only. There is no MCP server to connect and nothing to sign in to. You need an OpenKey key only when the code you are integrating runs, and the skills never ask for it: it lives in the `OPENKEY_API_KEY` environment variable.

## Claude Code

```text
/plugin marketplace add https://github.com/openkeyhq/skills
/plugin install openkey@openkey
```

The `owner/repo` shorthand clones over SSH by default; the `https://` form above works without an SSH key. The plugin adds both skills and the `/openkey:integrate` command.

## Cursor

```bash
npx skills add openkeyhq/skills -y --skill '*' --agent cursor
```

For the auto-attached rule, copy `rules/openkey.mdc` from this repository into `.cursor/rules/` in your project. It applies when you edit code that calls an LLM.

## Codex

```bash
npx skills add openkeyhq/skills -y --skill '*' --agent codex
```

## Any host

```bash
npx skills add openkeyhq/skills -y --skill '*' --agent '*'
# or, for Claude Code
gh skill install openkeyhq/skills --all --agent claude-code --scope user
```

`gh skill` needs GitHub CLI 2.90 or later.

## Updating

```bash
/plugin update openkey@openkey   # Claude Code plugin
npx skills update -y             # skills installed with npx
gh skill update --all            # skills installed with gh
```

## Check it worked

- Claude Code: `claude plugin list` shows `openkey`. Start a new session, or run `/reload-plugins`.
- Any host: `curl -s https://api.openkey.ai/v1/models | head -c 120` returns JSON. This is the live catalog the skills point agents to.

## Troubleshooting

- **`/plugin marketplace add` fails with an SSH error:** use the `https://github.com/openkeyhq/skills` form.
- **The skills do not appear:** a plugin installed from the shell loads in the next session. Start a new one.
- **Never paste a key into a skill, rule or tracked file.** Set `OPENKEY_API_KEY` in your environment or a gitignored `.env`.
