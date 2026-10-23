# Eval fixture projects

Cases name a project with `fixture_project:`. Each lives in `evals/projects/<name>/` and is a minimal invented app that uses another provider directly, as a real project would before switching to OpenKey. They need no install and are never run; the agent only reads and edits them. Keep them free of real company or person names.

| Project | What it holds |
|---|---|
| `py-openai` | `app.py` with `from openai import OpenAI` and `client = OpenAI()`, `requirements.txt`, `.gitignore` listing `.env` |
| `ts-openai` | `src/llm.ts` with `new OpenAI()`, `package.json`, `.gitignore` |
| `py-anthropic` | `app.py` with `anthropic.Anthropic()`, `requirements.txt`, `.gitignore` |
| `next-chat` | `app/page.tsx`, a `"use client"` component that calls OpenAI from the browser with `dangerouslyAllowBrowser: true` |
| `py-litellm` | `app.py` calling `litellm.completion(model="gpt-4o", …)` |

These files deliberately contain pre-OpenKey code, so the pack lint's model-id check (which only scans `skills/`, `commands/` and `rules/`) does not apply to them.
