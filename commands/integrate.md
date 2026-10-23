---
description: Integrate OpenKey into this project
argument-hint: [what to switch, e.g. "all OpenAI calls"]
allowed-tools: [Read, Glob, Grep, "Edit(./**)", "Write(./**)", "WebFetch(domain:api.openkey.ai)", "WebFetch(domain:openkey.ai)"]
disable-model-invocation: true
---

# Integrate OpenKey

## Arguments

The user invoked this command with: $ARGUMENTS

If empty, switch every LLM client found in step 2.

## Instructions

When this command is invoked:

1. Load the `openkey` skill. Its rules win over anything below.
2. Find the LLM clients: Grep for `openai|anthropic|google.genai|litellm|@ai-sdk|langchain`, and for HTTP calls to the providers' own hosts. Limit the list to what `$ARGUMENTS` names.
3. For each client, apply skill sections 2 and 3: swap the base URL and key, and write each model id as `provider/model` after confirming it against the live catalog.
4. Read `.env.example` and `.gitignore` first. Add `OPENKEY_API_KEY=` to `.env.example` and make sure `.env` is gitignored, adding only the missing lines. Never write a key into any file.
5. Apply skill section 4. Run the changed code only if the user asked for it; otherwise end with the commands for them to run.
6. Report the files changed and anything skipped, with the reason.
