# Contributing

Thank you. This pack is generated from a private development repository, so a pull request here is reviewed, then ported and released from there. Small fixes land quickly; new skills need a short discussion first, using the skill request template.

## Rules every skill follows

- **Frontmatter uses only the Agent Skills fields**: `name`, `description`, `license: MIT` and `compatibility`. No other key, because the spec validator rejects them.
- **`name` equals the directory name**, starts with `openkey`, and contains neither `anthropic` nor `claude`.
- **The description is a routing contract.** Third person, at most 1024 characters, with the literal `Use when:` followed by the phrases a user actually says, and the literal `NOT for:` naming the sibling skill that owns each excluded case.
- **Thin by design.** The body stays under 300 lines. Tables and matrices live in flat `references/*.md` files, each linked from the skill and listed under `## Load on demand`.
- **Volatile facts come from live calls.** Model ids, prices and limits are read from `GET https://api.openkey.ai/v1/models` and the docs at run time, never written as fact in a skill. An example may cite only a model id or URL listed in `scripts/live_facts.json`. To add one, edit that file and run `python3 scripts/check_live.py`: it must pass against production.
- **Keys never appear.** Code reads `OPENKEY_API_KEY`. Examples use `$OPENKEY_API_KEY` or the `sk-ok-…` placeholder, never a real key.
- **No OpenKey SDK install commands.** Integrations swap the base URL in the OpenAI, Anthropic or Gemini SDK, or use plain HTTP.
- **Public-safe.** No real people, no client or customer brands, no internal details, no secrets. Examples use invented project names.

## Before opening a pull request

1. Write at least three eval cases first, in `evals/cases/`, before the skill body. See `evals/README.md`.
2. Validate: `uvx --from skills-ref==0.1.1 agentskills validate skills/<name>`.
3. Run every gate locally: `scripts/check.sh`. It is the source of truth; there is no CI. The maintainer runs the same script before merging.
4. Fill in the pull request template. Its checklist covers what a machine cannot check.

## Requesting a new skill

Open a skill request issue. The one question that decides it: why is this a separate skill rather than a row in an existing one? If it fits an existing skill, it should go there.

## How pull requests land

Nothing is merged on this repository directly. A pull request is reviewed here by the maintainer, then ported upstream and shipped in the next release with credit in `CHANGELOG.md`; that way a merged change is never lost to the next sync. Expect a reply on the pull request rather than a merge button.
