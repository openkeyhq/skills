# Cursor, Cline, Zed and Continue on OpenKey

All four speak the OpenAI API: base URL `https://api.openkey.ai/v1`, the OpenKey key, and a model id. They are set per user in each tool's own settings. The user enters the key in the tool; the agent never writes it into a file.

| Tool | Status | Headers |
|---|---|---|
| Cursor | Unverified: OpenKey has not checked the override against current Cursor docs. Say so to the user | None |
| Cline | Verified | None on the OpenAI Compatible provider |
| Zed | Verified | None |
| Continue | Should work: the shape is right, not run end to end | `requestOptions.headers` |

## Cursor (unverified)

Cursor → Settings → Models → API Keys:

- **OpenAI API Key**: the user's OpenKey key.
- **Override OpenAI Base URL**: `https://api.openkey.ai/v1`. Turn the override toggle on, then click **Verify**; the check request shows on the Activity page of the OpenKey app.
- **Model**: `openkey/auto`, or any `provider/model` id from `https://api.openkey.ai/v1/models`.
- Caveat: while the base-URL override is on, Cursor-native features (Tab autocomplete, built-in models) are unavailable, because Cursor routes everything through the override.

## Cline

Cline → Settings → API Provider: **OpenAI Compatible**:

- **Base URL**: `https://api.openkey.ai/v1`
- **API Key**: the user's OpenKey key
- **Model ID**: `openkey/auto`

Start a task; every step is metered and shows on the Activity page.

## Zed

Add the provider to Zed's `settings.json`. If the file already has settings, read it and merge this in; keep everything else.

```json
{
  "language_models": {
    "openai_compatible": {
      "OpenKey": {
        "api_url": "https://api.openkey.ai/v1",
        "available_models": [{ "name": "openkey/auto", "max_tokens": 200000 }]
      }
    }
  }
}
```

The key does not go in `settings.json`: the user enters it in the Agent panel → Settings → OpenKey. Then pick **OpenKey · openkey/auto** in the Agent panel.

## Continue

A model block in `~/.continue/config.yaml`, a per-user file outside the project. The user replaces the placeholder with their own key:

```yaml
models:
  - name: OpenKey
    provider: openai
    model: openkey/auto
    apiBase: https://api.openkey.ai/v1
    apiKey: sk-ok-…
    requestOptions:
      headers:
        X-OpenKey-Tags: project=atlas
```

`requestOptions` is optional; `atlas` stands for the project. Reload the window and pick **OpenKey** in the model dropdown.

## Attribution without headers

Cursor, Cline and Zed have no header field. Give each such tool its own OpenKey key and set that key's attribution defaults (customer, tags) in the OpenKey app; the gateway applies them server-side to every request on the key.

OpenKey's docs also describe attribution links pasted as the base URL. They do not resolve in production; never use one.
