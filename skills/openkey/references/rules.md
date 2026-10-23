# OpenKey integration rules

Section 5 of the skill as a checklist, so the rules travel with any single file of it.

- Code reads the key from `OPENKEY_API_KEY`; in Node, check it is set before building the client. No key in any file, `.env` included. `.env.example` gets `OPENKEY_API_KEY=` with no value, and `.env` is gitignored.
- Never ask for the key and never repeat one the user pasted. Suggest rotating a pasted key in the OpenKey app.
- No key and no OpenKey call in browser code: CORS blocks the `X-OpenKey-*` headers. Move the call behind a server route.
- No OpenKey SDK install. No new dependency either, except the one provider package the skill's frameworks reference names for a framework: the project's own SDK, or plain HTTP with `requests`, `httpx`, `fetch` or `curl`.
- Base URLs: OpenAI dialect `https://api.openkey.ai/v1`; Anthropic and Gemini `https://api.openkey.ai`, with no `/v1`. No other host or path prefix.
- Model ids are `provider/model`, each confirmed in the free list `GET https://api.openkey.ai/v1/models` before it is written, and called out as unconfirmed when it could not be. `openkey/auto` is valid on chat surfaces but is not in that list.
- An unknown `X-OpenKey-Warning` code is logged, never fatal.
