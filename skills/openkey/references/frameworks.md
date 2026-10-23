# Frameworks and other clients

Frameworks reach OpenKey through their OpenAI-compatible provider: base URL `https://api.openkey.ai/v1`, the key from `OPENKEY_API_KEY`, and a `provider/model` id. `openkey/auto` lets the gateway pick the model on chat calls.

## Vercel AI SDK

Use the OpenAI-compatible provider, `@ai-sdk/openai-compatible`. If the project does not have it yet, it is the one package to add (`npm i @ai-sdk/openai-compatible`); say so to the user.

```ts
import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import { generateText } from "ai";

const apiKey = process.env.OPENKEY_API_KEY;
if (!apiKey) throw new Error("OPENKEY_API_KEY is not set");

const openkey = createOpenAICompatible({
  name: "openkey",
  baseURL: "https://api.openkey.ai/v1",
  apiKey,
});

const { text } = await generateText({
  model: openkey("openkey/auto"),
  prompt: "Hello!",
});
```

Streaming and tools work unchanged. Any `provider/model` id goes in place of `openkey/auto`, for example `openkey("anthropic/claude-sonnet-4.5")`.

## LangChain (Python)

`ChatOpenAI` from `langchain-openai` with a base URL:

```python
import os
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="openkey/auto",
    base_url="https://api.openkey.ai/v1",
    api_key=os.environ["OPENKEY_API_KEY"],
)
print(llm.invoke("Hello!").content)
```

Chains, agents and tools run unchanged.

## Any other client

A library, framework or tool not covered above still works if it can talk to an OpenAI-compatible endpoint. Do not look for an OpenKey package or plugin for it, and do not invent one.

1. Find its setting for the endpoint: often called base URL, API base, endpoint, host or server URL. Change only the host in the client's default base URL and keep its path. If the default ends in `/v1` (`https://api.openai.com/v1`), use `https://api.openkey.ai/v1`; if it is a bare host (the Mistral SDK's `server_url` `https://api.mistral.ai`, the Anthropic SDKs), use `https://api.openkey.ai`. Requests must land on `/v1/chat/completions` or `/v1/messages`; `/v1/v1/…` or a bare `/messages` returns 404. Write it in the code where the client or call is configured.
2. Find its API key setting and read `OPENKEY_API_KEY` from the environment there.
3. Pass the OpenKey id, `provider/model`. Some libraries choose their wire protocol from a prefix on the model name. Pick the prefix their own docs give for a custom OpenAI-compatible endpoint, and put the full OpenKey id after it.
4. If you are not sure how the library takes a base URL, check the client's default base URL and how it takes one, in its docs or its source in the project's dependencies, rather than guessing, and tell the user what you could not confirm.
