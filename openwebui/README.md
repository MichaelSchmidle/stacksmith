# Open WebUI Stack

Open WebUI is a self-hosted chat interface that works with OpenAI-compatible APIs. In this Stacksmith setup, Open WebUI should usually talk to the shared LiteLLM proxy instead of directly to each model provider.

Official docs:

- [Open WebUI home](https://docs.openwebui.com/)
- [Quick start with Docker](https://docs.openwebui.com/getting-started/quick-start/)
- [Starting with OpenAI-compatible APIs](https://docs.openwebui.com/getting-started/quick-start/starting-with-openai)
- [Environment variable reference](https://docs.openwebui.com/reference/env-configuration/)

## What this stack assumes

- Open WebUI runs in Docker on the `stacksmith` network.
- LiteLLM exposes an OpenAI-compatible API through a Traefik-routed hostname such as `https://llm.example.com/v1`.
- LM Studio, vLLM, hosted APIs, and other model endpoints are configured in LiteLLM.

This keeps Open WebUI provider-neutral: add or change model backends in LiteLLM, not in every UI client.

## Quick start

1. Deploy LiteLLM first if you want the shared proxy pattern.

2. Copy the Open WebUI environment file:

```bash
cp openwebui/.env.example openwebui/.env
```

3. Edit `openwebui/.env`:

```bash
OPEN_WEBUI_HOSTNAME=ai.yourdomain.com
OPENAI_API_BASE_URL=https://llm.yourdomain.com/v1
OPENAI_API_KEY=sk-you...
```

4. Start Open WebUI:

```bash
docker compose --env-file openwebui/.env -f openwebui/docker-compose.yml up -d
```

5. Open the UI through Traefik:

```text
https://ai.yourdomain.com
```

## Notes

- Open WebUI listens on container port `8080`; Traefik routes to that hard-coded internal port via the Compose label.
- This stack does not publish a host port. Access is expected through Traefik.
- If you skip LiteLLM, `OPENAI_API_BASE_URL` can still point directly at any OpenAI-compatible endpoint reachable from the Open WebUI container.
- If LiteLLM and Open WebUI are deployed from separate Compose invocations, they do not need to share a Docker network as long as Open WebUI can reach the configured LiteLLM hostname.

## Validation pattern

Before blaming the UI, validate LiteLLM from the Open WebUI host:

```bash
curl -fsS https://llm.yourdomain.com/health/liveliness
curl -fsS -H "Authorization: Bearer *** key>" https://llm.yourdomain.com/v1/models
```

If those work from the host, use the same base URL in `OPENAI_API_BASE_URL`.
