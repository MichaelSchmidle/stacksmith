# LiteLLM Stack

LiteLLM is an OpenAI-compatible proxy for routing UI clients to local and hosted model providers. In Stacksmith, it becomes the shared model gateway for Open WebUI, Open Design, LM Studio, vLLM, Ollama-compatible endpoints, and hosted APIs.

Official sources:

- [LiteLLM proxy docs](https://docs.litellm.ai/docs/proxy/deploy)
- [LiteLLM Docker Compose example](https://github.com/BerriAI/litellm/blob/main/docker-compose.yml)

## What this stack assumes

- LiteLLM runs on the external `stacksmith` network.
- Traefik handles HTTPS on the Tailscale-facing entrypoint.
- PostgreSQL stores LiteLLM configuration, virtual keys, budgets, and model/provider entries.
- Model endpoints are managed in LiteLLM, then clients use LiteLLM's `/v1` API.

## Architecture

```text
Open WebUI ─┐
Open Design ├─> LiteLLM proxy ─> LM Studio / vLLM / OpenAI / Anthropic / ...
Other apps ─┘
```

Recommended internal base URL for containers on the `stacksmith` network:

```text
http://litellm:4000/v1
```

Recommended external/admin URL through Traefik:

```text
https://litellm.yourdomain.com
```

## Quick start

1. Copy the environment file:

```bash
cp litellm/.env.example litellm/.env
```

2. Generate secrets and edit `litellm/.env`:

```bash
openssl rand -hex 32
```

Set at least:

```bash
LITELLM_HOSTNAME=litellm.yourdomain.com
LITELLM_MASTER_KEY=sk-your-generated-secret
LITELLM_SALT_KEY=your-generated-secret
LITELLM_UI_USERNAME=admin
LITELLM_UI_PASSWORD=change-me
LITELLM_POSTGRES_PASSWORD=change-me
```

3. Start the stack:

```bash
docker compose --env-file litellm/.env -f litellm/docker-compose.yml up -d
```

4. Open the LiteLLM UI through Traefik/Tailscale and add provider endpoints.

## Adding LM Studio

Expose LM Studio on a network-reachable interface, then add it in LiteLLM as an OpenAI-compatible endpoint.

Typical settings:

- Provider: OpenAI Compatible
- API base: `http://host.docker.internal:1234/v1` for same-host Docker-to-host access, or a Tailscale/LAN URL for another host
- API key: any non-empty value if LM Studio does not enforce auth
- Model: the exact model ID served by LM Studio

Then point clients at LiteLLM instead of directly at LM Studio.

## Client configuration

Open WebUI:

```bash
OPENAI_API_BASE_URL=http://litellm:4000/v1
OPENAI_API_KEY=sk-your-litellm-key
```

Open Design:

```text
Base URL: http://litellm:4000/v1
API key: sk-your-litellm-key
```

## Validation pattern

Check service health:

```bash
docker compose --env-file litellm/.env -f litellm/docker-compose.yml ps
docker compose --env-file litellm/.env -f litellm/docker-compose.yml logs -f litellm
```

Check the OpenAI-compatible API:

```bash
curl -fsS -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  http://127.0.0.1:${LITELLM_PORT}/v1/models
```

## Updates

```bash
docker compose --env-file litellm/.env -f litellm/docker-compose.yml pull
docker compose --env-file litellm/.env -f litellm/docker-compose.yml up -d
```

## Backup

Back up the PostgreSQL volume:

```bash
docker run --rm \
  -v stacksmith_litellm_db_data:/var/lib/postgresql/data:ro \
  -v "$(pwd)":/backup \
  alpine tar czf /backup/litellm-db-data.tar.gz /var/lib/postgresql/data
```
