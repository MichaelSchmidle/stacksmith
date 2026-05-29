# Open Design Stack

Open Design is a local-first, web-based design workspace that delegates generation work to coding agents or BYOK model APIs. This Stacksmith bundle follows the official single-container Docker deployment, with Traefik/Tailscale routing added for private HTTPS access.

Official sources:

- [Open Design site](https://open-design.ai/)
- [Open Design GitHub](https://github.com/nexu-io/open-design)
- [Docker deployment notes](https://github.com/nexu-io/open-design/tree/main/deploy)

## What this stack assumes

- Open Design runs in Docker on the external `stacksmith` network.
- Traefik handles HTTPS on the Tailscale-facing entrypoint.
- The container stores projects, conversations, artifacts, and SQLite data in the named Docker volume `stacksmith_open_design_data`.
- Model/provider configuration should live in Open Design itself or in a shared proxy such as the `litellm/` stack, not in extra Open Design tool volumes.

## Security model

Open Design's own deployment docs warn not to publish the daemon directly on a public or shared LAN interface. This stack therefore:

- binds the direct host port to loopback only
- routes browser access through Traefik's `websecure-tailscale` entrypoint
- requires an `OD_API_TOKEN`
- restricts browser API origins via `OPEN_DESIGN_ALLOWED_ORIGINS`

Keep the hostname reachable only through Tailscale/DNS that resolves to the Tailscale-facing Traefik interface.

## Quick start

1. Copy the environment file:

```bash
cp opendesign/.env.example opendesign/.env
```

2. Generate a daemon token:

```bash
openssl rand -hex 32
```

3. Edit `opendesign/.env`:

```bash
OPEN_DESIGN_HOSTNAME=design.yourdomain.com
OPEN_DESIGN_ALLOWED_ORIGINS=https://design.yourdomain.com
OD_API_TOKEN=<generated-token>
```

4. Start the stack:

```bash
docker compose --env-file opendesign/.env -f opendesign/docker-compose.yml up -d
```

5. Open the UI:

- Through Traefik/Tailscale: `https://design.yourdomain.com`
- Direct local loopback: `http://127.0.0.1:7456`

## Using LiteLLM

If you deploy the companion `litellm/` stack, configure Open Design to use the LiteLLM proxy base URL instead of binding Open Design to a particular local model runtime:

```text
http://litellm:4000/v1
```

From there, add LM Studio, vLLM, OpenAI, Anthropic, or other providers in LiteLLM and keep Open Design provider-neutral.

## Validation pattern

Check that the container is healthy:

```bash
docker compose --env-file opendesign/.env -f opendesign/docker-compose.yml ps
docker compose --env-file opendesign/.env -f opendesign/docker-compose.yml logs -f open-design
```

Check the health endpoint through the container:

```bash
docker compose --env-file opendesign/.env -f opendesign/docker-compose.yml exec open-design \
  node -e "fetch('http://127.0.0.1:7456/api/health').then(r=>r.text()).then(t=>console.log(t))"
```

## Updates

```bash
docker compose --env-file opendesign/.env -f opendesign/docker-compose.yml pull
docker compose --env-file opendesign/.env -f opendesign/docker-compose.yml up -d
```

## Backup

Back up the named volume:

```bash
docker run --rm \
  -v stacksmith_open_design_data:/data:ro \
  -v "$(pwd)":/backup \
  alpine tar czf /backup/open-design-data.tar.gz /data
```

Restore into an empty volume:

```bash
docker run --rm \
  -v stacksmith_open_design_data:/data \
  -v "$(pwd)":/backup \
  alpine tar xzf /backup/open-design-data.tar.gz -C /
```
