# OpenKey Skills

[Agent Skills](https://agentskills.io/specification) that teach Claude Code, Cursor and Codex to work with [OpenKey](https://openkey.ai), an LLM gateway with one key and OpenAI-, Anthropic- and Gemini-compatible endpoints. One skill puts OpenKey into your app's code. The other runs your coding agent through OpenKey.

The skills are thin by design. They state the stable wire facts and send the agent to the live catalog and docs for model ids, prices and parameters, so the pack does not go stale when the catalog moves. They make no calls with your key and need no MCP server.

## Installing

These skills work with any agent that supports the Agent Skills standard.

### Claude Code

Install using the [plugin marketplace](https://code.claude.com/docs/en/discover-plugins). Use the `https://` form: the `owner/repo` shorthand clones over SSH.

```text
/plugin marketplace add https://github.com/openkeyhq/skills
/plugin install openkey@openkey
```

### Cursor

```bash
npx skills add openkeyhq/skills -y --skill '*' --agent cursor
```

This installs the skills. For the auto-attached rule, copy `rules/openkey.mdc` into your project's `.cursor/rules/`.

### Codex

```bash
npx skills add openkeyhq/skills -y --skill '*' --agent codex
```

### npx skills, any agent

```bash
npx skills add openkeyhq/skills -y --skill '*' --agent '*'
```

### gh skill

```bash
gh skill install openkeyhq/skills --all --agent claude-code --scope user
```

Full steps, updating and troubleshooting are in [INSTALL.md](INSTALL.md). An agent installing this for you should follow [INSTALL_FOR_AGENTS.md](INSTALL_FOR_AGENTS.md).

## Commands

Commands are slash commands you call explicitly.

| Command | Description |
|---|---|
| `/openkey:integrate` | Integrate OpenKey into the current project: find the LLM calls, switch the base URL and key, and check the model ids against the live catalog. Takes an optional scope, for example `/openkey:integrate all OpenAI calls`. |

## Skills

Skills load on their own when a request matches their triggers.

| Skill | What it does |
|---|---|
| [`openkey`](skills/openkey/SKILL.md) | Useful for putting OpenKey into an app's code: base URL, key from `OPENKEY_API_KEY`, `provider/model` ids, errors and headers. |
| [`openkey-coding-agents`](skills/openkey-coding-agents/SKILL.md) | Useful for running Claude Code, Codex CLI, Cursor, Cline, Zed or Continue on OpenKey, per user or as committed team config tagged by project. |

## Resources

- [OpenKey docs](https://openkey.ai/llms.txt), the index the skills read first
- [Model catalog](https://openkey.ai/models)
- [Live model ids](https://api.openkey.ai/v1/models), no key needed
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md) and [security policy](SECURITY.md)

## Licence

MIT. See [LICENSE](LICENSE).
