# OpenAI SDK and OpenAI-shaped HTTP

## Contents

- Chat: Python, TypeScript, Go, curl
- Streaming
- Embeddings
- Responses API

The OpenAI dialect lives under the base URL `https://api.openkey.ai/v1`, with the key sent as `Authorization: Bearer`. The SDKs build that header from `api_key` / `apiKey`. Model ids are `provider/model`, and a chat model from any lab works through this client: change the string, keep the SDK.

## Chat

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://api.openkey.ai/v1",
    api_key=os.environ["OPENKEY_API_KEY"],
)

completion = client.chat.completions.create(
    model="openai/gpt-4o",
    messages=[{"role": "user", "content": "Hello"}],
)
print(completion.choices[0].message.content)
```

```ts
import OpenAI from "openai";

// Unset, an undefined apiKey would make the SDK fall back to OPENAI_API_KEY.
const apiKey = process.env.OPENKEY_API_KEY;
if (!apiKey) throw new Error("OPENKEY_API_KEY is not set");

const client = new OpenAI({
  baseURL: "https://api.openkey.ai/v1",
  apiKey,
});

const completion = await client.chat.completions.create({
  model: "openai/gpt-4o",
  messages: [{ role: "user", content: "Hello" }],
});
console.log(completion.choices[0].message.content);
```

```go
client := openai.NewClient(
	option.WithAPIKey(os.Getenv("OPENKEY_API_KEY")),
	option.WithBaseURL("https://api.openkey.ai/v1"),
)
chat, err := client.Chat.Completions.New(context.Background(), openai.ChatCompletionNewParams{
	Model:    "openai/gpt-4o",
	Messages: []openai.ChatCompletionMessageParamUnion{openai.UserMessage("Hello")},
})
if err != nil {
	return err
}
fmt.Println(chat.Choices[0].Message.Content)
```

The Go imports are `github.com/openai/openai-go` and `github.com/openai/openai-go/option`.

```bash
curl https://api.openkey.ai/v1/chat/completions \
  -H "Authorization: Bearer $OPENKEY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-4o",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## Streaming

Set `stream: true`. The response is server-sent events.

- Each event is `data: <json>`, with no `event:` names, and the stream ends with the literal `data: [DONE]`.
- A stream that ends with neither `[DONE]` nor a final chunk is incomplete, not a success.
- With `stream_options: {"include_usage": true}` the last chunk carries `usage` and an empty `choices`.
- Every `X-OpenKey-*` header is sent before the first chunk. The provider is never swapped once a stream has started.
- After the stream opens the status stays `200`. A failure arrives as a `data:` event with a top-level `error` object, still followed by `[DONE]`. The OpenAI SDKs raise an API error from the stream loop when they see it. Treat it as a failed call and do not retry automatically: part of the answer was already delivered.

```python
stream = client.chat.completions.create(
    model="openai/gpt-4o",
    stream=True,
    messages=[{"role": "user", "content": "Hello"}],
)
for chunk in stream:
    delta = chunk.choices[0].delta.content if chunk.choices else None
    if delta:
        print(delta, end="", flush=True)
```

```ts
const stream = await client.chat.completions.create({
  model: "openai/gpt-4o",
  stream: true,
  messages: [{ role: "user", content: "Hello" }],
});
for await (const chunk of stream) {
  const delta = chunk.choices[0]?.delta?.content;
  if (delta) process.stdout.write(delta);
}
```

With curl, add `-N` so the events print as they arrive.

## Embeddings

`POST /v1/embeddings`, with the same client.

```python
resp = client.embeddings.create(
    model="openai/text-embedding-3-small",
    input=["first text", "second text"],
)
vectors = [d.embedding for d in resp.data]
```

Other embedding models are in the public catalog (`GET https://api.openkey.ai/api/public/v1/models`); their ids are `provider/model` like any other.

## Responses API

`POST /v1/responses` is served too. Use the OpenAI SDK's `responses` resource with the same client.

```python
resp = client.responses.create(
    model="openai/gpt-4o",
    input="Hello",
)
print(resp.output_text)
```

On a streamed Responses call, an error event has no class field, because `type` there is the event name; branch on its `code`.
