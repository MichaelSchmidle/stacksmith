# Voicebox Stack

Voicebox is a local-first AI voice studio for voice cloning, text-to-speech, dictation, and MCP/REST voice I/O. This Stacksmith stack runs the headless Docker web UI/API plus an authenticated OpenAI-compatible TTS sidecar behind Traefik.

Official docs:

- [Voicebox Docker deployment](https://docs.voicebox.sh/overview/docker)
- [Voicebox GPU acceleration](https://docs.voicebox.sh/overview/gpu-acceleration)
- [Voicebox MCP server](https://docs.voicebox.sh/overview/mcp-server)
- [Voicebox API](https://voicebox.sh/#api)

## What this stack assumes

- Voicebox runs on a Docker host with the NVIDIA Container Toolkit installed when GPU acceleration is desired.
- Browser/API access is routed through Traefik on the `stacksmith` network.
- Voicebox listens on container port `17493`; Traefik routes to that fixed internal port.
- Voicebox has no built-in authentication, so it should stay Tailscale/VPN-only or sit behind an auth middleware before broader exposure.
- Upstream Docker currently builds from source; prebuilt GHCR images are documented as coming later, not available now.
- The adapter is a prebuilt multi-architecture image pinned by semantic version and immutable manifest digest. Portainer never builds adapter source.
- Only `/v1/audio/*` routes to the bearer-authenticated adapter. Existing Voicebox UI/API routes continue to target Voicebox.

## Quick start

1. Copy the environment template:

```bash
cp voicebox/.env.example voicebox/.env
```

2. Edit `voicebox/.env`:

```bash
VOICEBOX_HOSTNAME=voicebox.yourdomain.com
VOICEBOX_CORS_ORIGINS=https://voicebox.yourdomain.com
VOICEBOX_MEMORY_LIMIT=16G
VOICEBOX_NVIDIA_GPU_COUNT=1
VOICEBOX_ADAPTER_API_KEY=replace-with-a-long-random-secret
```

3. Build the image on the Docker host:

```bash
docker compose --env-file voicebox/.env -f voicebox/docker-compose.yml -f voicebox/docker-compose.build.yml build
```

4. Start Voicebox:

```bash
docker compose --env-file voicebox/.env -f voicebox/docker-compose.yml up -d
```

5. Open the UI through Traefik:

```text
https://voicebox.yourdomain.com
```

6. Check the routed API through Traefik:

```bash
curl -fsS https://voicebox.yourdomain.com/health
curl -fsS https://voicebox.yourdomain.com/profiles
```

## OpenAI-compatible TTS sidecar

The sidecar translates synchronous OpenAI speech requests into Voicebox's asynchronous generation flow:

```text
POST /v1/audio/speech -> POST /speak -> status SSE -> GET /audio/{id}
```

It has no host port, database, or audio cache. It runs as UID/GID `10001`, with a read-only root filesystem, all Linux capabilities dropped, and a bounded `/tmp` tmpfs for format conversion. The configured Voicebox URL is fixed to the internal Compose service and cannot be caller-controlled.

The external endpoint requires a bearer token:

```bash
curl --fail-with-body \
  --request POST https://voicebox.yourdomain.com/v1/audio/speech \
  --header "Authorization: Bearer ${VOICEBOX_ADAPTER_API_KEY}" \
  --header "Content-Type: application/json" \
  --output speech.mp3 \
  --data '{"model":"tts-1","voice":"profile-name-or-id","input":"Adapter ready.","response_format":"mp3"}'
```

Unauthenticated requests to `/v1/audio/*` fail at the adapter. The broader Voicebox application remains unauthenticated and therefore must remain on a trusted private route.

### Open WebUI

Configure **Admin Settings -> Audio** using the deployed values:

```text
TTS engine: OpenAI
API base URL: https://voicebox.yourdomain.com/v1
API key: <VOICEBOX_ADAPTER_API_KEY>
Model: tts-1
Voice: <Voicebox profile name or UUID>
```

Open WebUI persists effective Audio settings in its database, so changing Compose defaults alone may not change an existing installation. Verify the Admin Settings values after redeployment.

Open WebUI may retain generated audio and request metadata containing spoken text in its speech cache; Voicebox separately keeps generation history/audio. Set an explicit retention policy for both stores.

### Adapter health

The adapter exposes `/healthz` for process liveness and `/readyz` for sanitized Voicebox readiness inside the Compose network. These paths are not routed through the public hostname; inspect them from the Docker network or use the container health status.

## Resource guidance

Voicebox docs call out **8GB RAM minimum** and **16GB+ recommended** for running multiple engines. If Voicebox shares a GPU host with a vLLM server, lower the vLLM reservation first; a practical starting point is:

```bash
VLLM_GPU_MEMORY_UTILIZATION=0.70
VLLM_MAX_MODEL_LEN=131072
```

That preserves a long-context serving profile while creating materially more headroom for Voicebox model loading and CUDA/PyTorch runtime overhead.

## API / MCP

Voicebox exposes REST and MCP on the routed hostname:

```bash
curl -X POST https://voicebox.yourdomain.com/speak \
  -H "Content-Type: application/json" \
  -H "X-Voicebox-Client-Id: hermes" \
  -d '{"text":"Deploy complete.","profile":"Morgan"}'
```

Documented MCP endpoint:

```text
https://voicebox.yourdomain.com/mcp
```

Tools include `voicebox.speak`, `voicebox.transcribe`, `voicebox.list_profiles`, and `voicebox.list_captures`.

## Volumes

| Volume | Container path | Purpose |
|---|---|---|
| `stacksmith_voicebox_data` | `/app/data` | Profiles, database, app data, and model/cache files under `/app/data/cache` |
| `stacksmith_voicebox_generations` | `/app/data/generations` | Generated audio files |

## Notes

- First build can take several minutes because it builds the frontend and installs Python/TTS dependencies.
- Model downloads are persisted under `/app/data/cache/huggingface` in the main `stacksmith_voicebox_data` volume.
- If CUDA out-of-memory errors appear, reduce the vLLM GPU reservation and/or Voicebox memory pressure before blaming Voicebox itself.
