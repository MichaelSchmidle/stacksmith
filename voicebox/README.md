# Voicebox Stack

Voicebox is a local-first AI voice studio for voice cloning, text-to-speech, dictation, and MCP/REST voice I/O. This Stacksmith service runs the headless Docker web UI/API behind Traefik.

Official docs:

- [Voicebox Docker deployment](https://docs.voicebox.sh/overview/docker)
- [Voicebox GPU acceleration](https://docs.voicebox.sh/overview/gpu-acceleration)
- [Voicebox MCP server](https://docs.voicebox.sh/overview/mcp-server)
- [Voicebox API](https://voicebox.sh/#api)

## What this stack assumes

- Voicebox runs on a Docker host with the NVIDIA Container Toolkit installed when GPU acceleration is desired.
- Browser/API access is routed through Traefik on the `stacksmith` network.
- The direct API port defaults to host loopback only: `${VOICEBOX_BIND_IP:-127.0.0.1}:${VOICEBOX_PORT}:17493`.
- Voicebox has no built-in authentication, so it should stay Tailscale/VPN-only or sit behind an auth middleware before broader exposure.
- Upstream Docker currently builds from source; prebuilt GHCR images are documented as coming later, not available now.

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
```

3. Build and start Voicebox:

```bash
docker compose --env-file voicebox/.env -f voicebox/docker-compose.yml up -d --build
```

4. Open the UI through Traefik:

```text
https://voicebox.yourdomain.com
```

5. Check the local API from the Docker host:

```bash
curl -fsS http://127.0.0.1:${VOICEBOX_PORT:-17493}/health
curl -fsS http://127.0.0.1:${VOICEBOX_PORT:-17493}/profiles
```

## Resource guidance

Voicebox docs call out **8GB RAM minimum** and **16GB+ recommended** for running multiple engines. If Voicebox shares a GPU host with a vLLM server, lower the vLLM reservation first; a practical starting point is:

```bash
VLLM_GPU_MEMORY_UTILIZATION=0.70
VLLM_MAX_MODEL_LEN=131072
```

That preserves a long-context serving profile while creating materially more headroom for Voicebox model loading and CUDA/PyTorch runtime overhead.

## API / MCP

Voicebox exposes REST and MCP on port `17493`:

```bash
curl -X POST http://127.0.0.1:17493/speak \
  -H "Content-Type: application/json" \
  -H "X-Voicebox-Client-Id: hermes" \
  -d '{"text":"Deploy complete.","profile":"Morgan"}'
```

Documented MCP endpoint:

```text
http://127.0.0.1:17493/mcp
```

Tools include `voicebox.speak`, `voicebox.transcribe`, `voicebox.list_profiles`, and `voicebox.list_captures`.

## Volumes

| Volume | Container path | Purpose |
|---|---|---|
| `stacksmith_voicebox_data` | `/app/data` | Profiles, database, app data |
| `stacksmith_voicebox_generations` | `/app/data/generations` | Generated audio files |
| `stacksmith_voicebox_huggingface_cache` | `/home/voicebox/.cache/huggingface` | Model cache |

## Notes

- First build can take several minutes because it builds the frontend and installs Python/TTS dependencies.
- Model downloads are persisted in the HuggingFace cache volume.
- If CUDA out-of-memory errors appear, reduce the vLLM GPU reservation and/or Voicebox memory pressure before blaming Voicebox itself.
