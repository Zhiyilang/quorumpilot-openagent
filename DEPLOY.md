# Deploy

## Local

```bash
python app.py            # http://localhost:7860, MCP at /gradio_api/mcp/
PORT=8080 python app.py
```

## Render (free tier)

`render.yaml` is included:

```yaml
services:
  - type: web
    name: quorumpilot
    env: python
    buildCommand: ""
    startCommand: python app.py
    envVars:
      - key: PORT
        value: "7860"
```

The app reads `PORT` and binds `0.0.0.0`. Connect the repo and deploy — no build step, the only dependency is Gradio.

## Hugging Face Space

1. New Space → SDK **Gradio** → create.
2. Add these files: `app.py`, `requirements.txt`, `README.md` (with `sdk: gradio` front matter), the whole `quorumpilot/` package, and `examples/`.
3. It boots on port 7860. MCP is served at `/gradio_api/mcp/`.

## Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 7860
CMD ["python", "app.py"]
```

## Health check

No dedicated endpoint is needed — `/` renders the UI. For uptime probes:

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:7860/
```

## Environment variables (all optional)

| Variable | Effect |
|---|---|
| `PORT` | HTTP port (default 7860) |
| `OPENAI_API_KEY` | adds a fifth, LLM member to the quorum |
| `OPENAI_BASE_URL` | any OpenAI-compatible endpoint (default `https://api.openai.com/v1`) |
| `OPENAI_MODEL` | model name (default `gpt-4o-mini`) |

For Gemini: `OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai`.

Without a key the quorum runs the four deterministic specialists and says so in the receipt. Nothing is degraded except the number of opinions.
