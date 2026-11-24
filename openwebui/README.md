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

## Optional: Reverie

[Reverie for Open WebUI](https://github.com/memrok-com/reverie-openwebui) adds
memory to opted-in folders. It requires stock Open WebUI **0.13.4** and a released
Linux amd64 adapter image. Use `docker-compose.reverie.yml` as the **additional**
Compose file after `docker-compose.yml`, not as another stack. For Portainer,
add `openwebui/docker-compose.reverie.yml` to that Git stack's additional paths;
keep the existing primary path, project, Traefik route and chat volume.

- Set `STACKSMITH_OPEN_WEBUI_IMAGE` to the immutable image digest of the already
  running, verified Open WebUI 0.13.4 install. If it is not 0.13.4, handle the
  version change separately; do not let enabling Reverie pull a different UI.
- Set `REVERIE_IMAGE` to the released `ghcr.io/memrok-com/reverie-openwebui`
  image digest, and set a dedicated `REVERIE_ADAPTER_TOKEN` through the stack
  environment. Do not store it in Git; both services receive it.
- Set `REVERIE_REFLECTION_URL` to the configured LiteLLM chat-completions URL
  (including `/v1/chat/completions`) and `REVERIE_REFLECTION_MODEL` to its model
  alias. Set `REVERIE_REFLECTION_API_KEY` privately if needed, and use
  `REVERIE_REFLECTION_REASONING_EFFORT=none` only if that route supports it.
  The sidecar has no published port, Traefik route, or provider credential.

Render and inspect the composed configuration privately before applying it; it
contains secrets. When using the CLI, pass `-f openwebui/docker-compose.yml`
then `-f openwebui/docker-compose.reverie.yml` to commands for this project. Follow the
adapter's [installation and first-use instructions](https://github.com/memrok-com/reverie-openwebui#add-to-an-existing-installation)
for the native Functions and preset. Starting the sidecar alone does not install them.

To disable, first follow the adapter's native Function/preset disable steps and
verify an ordinary chat. Then remove the additional Compose file and adapter
environment entries, but **keep `STACKSMITH_OPEN_WEBUI_IMAGE` pinned**. Reconcile
the removed `reverie` service in the same project and verify that both
`stacksmith_open_webui_data` and the project's `reverie-data` volume remain.
Never remove volumes to turn Reverie off. This is not a restore procedure.

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
