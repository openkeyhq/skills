# Install OpenKey skills

You are an AI agent. The user asked you to install the OpenKey skills. Follow these steps exactly, verify each one, and report at the end. There is no server to register and no sign-in.

## 1. Install the skills

Pick the first row that matches your host. These are shell commands; run them with your shell tool.

| Host | Run | Verify |
|---|---|---|
| Claude Code | `claude plugin marketplace add https://github.com/openkeyhq/skills` then `claude plugin install openkey@openkey` | `claude plugin list` shows `openkey` |
| Codex | `npx skills add openkeyhq/skills -y --skill '*' --agent codex` | a skill named `openkey` is installed |
| Cursor | `npx skills add openkeyhq/skills -y --skill '*' --agent cursor` | a skill named `openkey` is installed |
| Anything else | `npx skills add openkeyhq/skills -y --skill '*' --agent '*'` | same |

A plugin installed from the shell loads in the next session. On Claude Code, ask the user to run `/reload-plugins`; elsewhere, ask them to start a new session.

## 2. Verify and report

Run `curl -s https://api.openkey.ai/v1/models | head -c 120`. It returns JSON. This is the live model catalog the skills point to; it needs no key.

Tell the user, in three lines at most: the skills are installed, the catalog answered, and one thing to try, for example "switch this project's OpenAI calls to OpenKey". Do not explain file paths or internals. Do not ask for, print or store an API key.

## If something fails

| Symptom | Do |
|---|---|
| `claude plugin marketplace add` fails with an SSH error | Use the `https://github.com/openkeyhq/skills` form, as written above |
| `claude plugin list` does not show `openkey` | Ask the user to run `/reload-plugins` or start a new session, then check again |
| The `curl` returns no JSON | Say so and stop; the install itself does not depend on it |
| The skills command fails | Say what failed and stop |
