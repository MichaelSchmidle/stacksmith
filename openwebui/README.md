# Open WebUI Stack

Open WebUI is a self-hosted chat interface that works with OpenAI-compatible APIs, including the NVIDIA TensorRT-LLM stack in this repo.

Official docs:

- [Open WebUI home](https://docs.openwebui.com/)
- [Quick start with Docker](https://docs.openwebui.com/getting-started/quick-start/)
- [Starting with OpenAI-compatible APIs](https://docs.openwebui.com/getting-started/quick-start/starting-with-openai)
- [Environment variable reference](https://docs.openwebui.com/reference/env-configuration/)

## What this stack assumes

- Open WebUI runs in Docker on the `stacksmith` network.
- Your LLM backend exposes an OpenAI-compatible API on a network-reachable address.
- The backend may be on the same Docker host or on a different machine over LAN or Tailscale.

Examples:

```text
# Same host, using its LAN or Tailscale IP
http://100.76.167.25:8355/v1

# Different host on the same tailnet
http://llm-box.tailnet-name.ts.net:8355/v1
```

The key point is that the inference stack must bind to a network-reachable interface instead of loopback-only `127.0.0.1`.

This keeps the Open WebUI design identical in both deployment modes:

- single-host: UI and inference run on the same machine, but the UI still points at the machine's reachable IP or Tailscale address
- dual-host: UI points at the inference machine's LAN or Tailscale address

## Quick start

1. Copy the environment file:

```bash
cp openwebui/.env.example openwebui/.env
```

2. Edit `openwebui/.env`:

```bash
OPEN_WEBUI_HOSTNAME=ai.yourdomain.com
OPENAI_API_BASE_URL=http://100.76.167.25:8355/v1
OPENAI_API_KEY=
```

3. Start the stack:

```bash
docker compose --env-file openwebui/.env -f openwebui/docker-compose.yml up -d
```

4. Open the UI:

- Direct local access: `http://127.0.0.1:3000`
- Through Traefik: `https://ai.yourdomain.com`

## Notes

- This stack exposes a local port for easy direct access and testing, even if Traefik is not running.
- `OPENAI_API_KEY` can be left empty if your local backend does not require auth.
- If you point Open WebUI at a different provider later, only `OPENAI_API_BASE_URL` and optionally `OPENAI_API_KEY` need to change.
- For the Stacksmith TensorRT-LLM stack, make sure the inference service binds to `0.0.0.0` or to a specific LAN/Tailscale IP so this URL is reachable from the UI container.

## Validation Pattern

Before blaming the UI, validate the backend URL directly from the Open WebUI host:

```bash
curl http://your-inference-host:8355/v1/models
```

If that works from the UI machine, Open WebUI should be able to use the same URL.
