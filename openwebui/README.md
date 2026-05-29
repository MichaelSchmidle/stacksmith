# Open WebUI Stack

Open WebUI is a self-hosted chat interface that works with OpenAI-compatible APIs. In this Stacksmith setup, Open WebUI should usually talk to the companion `litellm/` proxy instead of directly to each model provider.

Official docs:

- [Open WebUI home](https://docs.openwebui.com/)
- [Quick start with Docker](https://docs.openwebui.com/getting-started/quick-start/)
- [Starting with OpenAI-compatible APIs](https://docs.openwebui.com/getting-started/quick-start/starting-with-openai)
- [Environment variable reference](https://docs.openwebui.com/reference/env-configuration/)

## What this stack assumes

- Open WebUI runs in Docker on the `stacksmith` network.
- LiteLLM exposes an OpenAI-compatible API at `http://litellm:4000/v1`.
- LM Studio, vLLM, hosted APIs, and other model endpoints are configured in LiteLLM.

This keeps Open WebUI provider-neutral: add or change model backends in LiteLLM, not in every UI client.

## Quick start

1. Deploy LiteLLM first if you want the shared proxy pattern:

```bash
cp litellm/.env.example litellm/.env
docker compose --env-file litellm/.env -f litellm/docker-compose.yml up -d
```

2. Copy the Open WebUI environment file:

```bash
cp openwebui/.env.example openwebui/.env
```

3. Edit `openwebui/.env`:

```bash
OPEN_WEBUI_HOSTNAME=ai.yourdomain.com
OPENAI_API_BASE_URL=http://litellm:4000/v1
OPENAI_API_KEY=sk-your-litellm-key
```

4. Start Open WebUI:

```bash
docker compose --env-file openwebui/.env -f openwebui/docker-compose.yml up -d
```

5. Open the UI:

- Direct local access: `http://127.0.0.1:3000`
- Through Traefik: `https://ai.yourdomain.com`

## Notes

- This stack exposes a local port for easy direct access and testing, even if Traefik is not running.
- If you skip LiteLLM, `OPENAI_API_BASE_URL` can still point directly at any OpenAI-compatible endpoint reachable from the Open WebUI container.
- If LiteLLM and Open WebUI are deployed from separate Compose invocations, both must join the external `stacksmith` network.

## Validation pattern

Before blaming the UI, validate LiteLLM from the Open WebUI host:

```bash
curl -fsS http://127.0.0.1:4000/health/liveliness
curl -fsS -H "Authorization: Bearer <LiteLLM key>" http://127.0.0.1:4000/v1/models
```

If those work on the host and `http://litellm:4000/v1` works from the Docker network, Open WebUI should be able to use the proxy.
