# Voicebox Stack

Voicebox is a local-first AI voice studio for voice cloning, text-to-speech, dictation, and MCP/REST voice I/O. This Stacksmith stack runs the headless Docker web UI/API plus an authenticated OpenAI-compatible TTS sidecar behind Traefik.

Official docs:

- [Voicebox Docker deployment](https://docs.voicebox.sh/overview/docker)
- [Voicebox GPU acceleration](https://docs.voicebox.sh/overview/gpu-acceleration)
- [Voicebox MCP server](https://docs.voicebox.sh/overview/mcp-server)
- [Voicebox API](https://voicebox.sh/#api)

## What this stack assumes

- The default Voicebox image requires a Linux ARM64 host with an NVIDIA GPU, compatible CUDA 13 driver, and NVIDIA Container Toolkit. It is not an AMD64 image.
- Browser/API access is routed through Traefik on the `stacksmith` network.
- Voicebox listens on container port `17493`; Traefik routes to that fixed internal port.
- Voicebox has no built-in authentication, so it should stay Tailscale/VPN-only or sit behind an auth middleware before broader exposure.
- Voicebox uses the prebuilt [voicebox-container](https://github.com/MichaelSchmidle/voicebox-container) ARM64 CUDA packaging, not an official upstream image. `VOICEBOX_IMAGE` defaults to `ghcr.io/michaelschmidle/voicebox-container:latest`; override it with a version/digest when reproducibility is required.
- The default image runs as UID/GID `10001:10001`. Existing storage must be writable by that identity before deployment.
- The base stack permits registry pulls; the optional source-build overlay retains `pull_policy: never` for local builds.
- The adapter is a prebuilt multi-architecture image following `latest`, consistent with Stacksmith application-image policy. Portainer never builds adapter source. Override `VOICEBOX_ADAPTER_IMAGE` with a version/digest when reproducibility is required.
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

3. For a fresh installation, pull both configured images on the Docker host (for an existing installation, first complete the update checks below):

```bash
docker compose --env-file voicebox/.env -f voicebox/docker-compose.yml pull
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

## Portainer Git stack updates

Deploy `voicebox/docker-compose.yml` without the build override. Both default images
are registry-hosted, so **Re-pull image** can be used for an explicitly approved update.
Image publication or a repository change is not deployment acceptance. If Portainer
automatically updates from the tracked branch, merging into it is also a deployment
decision: keep that merge on hold until the checks below are complete.

Before updating an existing installation:

1. Record the running application version and exact image digest, retain the previous
   image, and take a recoverable, application-consistent backup of **both** named volumes.
   A tag rollback alone cannot reverse a database migration.
2. Review the [published image evidence and inherited security findings](https://github.com/MichaelSchmidle/voicebox-container/issues/3).
   Publication approval does not accept these risks for your deployment. Keep access
   private and restrict models, caches and uploaded media to trusted inputs.
3. Verify that the existing data, generations and cache files are writable by UID/GID
   `10001:10001`. An old root-owned volume is not repaired by switching images. Any
   ownership change or data migration needs its own backed-up, approved procedure;
   this stack does not run automatic `chown` or force the application to run as root.
4. Remove old `VOICEBOX_IMAGE` / `VOICEBOX_ADAPTER_IMAGE` environment overrides or
   set them to the intended registry references. Existing Portainer values win over
   Compose defaults; `VOICEBOX_IMAGE=stacksmith_voicebox:latest` will not switch itself.
   Preserve deliberate version/digest pins instead of overwriting them blindly.
5. Pull both configured images and update the stack only after deployment approval.
   With CLI-managed configuration, use the `pull` and `up -d` commands above. In Portainer,
   update from the approved Git revision with **Re-pull image** enabled for registry images.
6. Verify both containers are healthy, existing profiles and generations remain
   accessible, and a real authenticated `/v1/audio/speech` request succeeds. CUDA/Qwen
   image validation does not establish this stack's storage migration or adapter integration.

Both `latest` tags are mutable. Voicebox follows reviewed packaging promotions; the
adapter follows stable releases. Neither requires a host-side source build. The
Python-based Voicebox healthcheck does not require `curl` in the runtime image.

### Optional local source build

The upstream source-build path remains available, but is not the default registry
packaging and does not inherit its ARM64 CUDA validation. In `voicebox/.env`, explicitly
set `VOICEBOX_IMAGE=stacksmith_voicebox:latest` before using the build overlay, and
optionally change `VOICEBOX_BUILD_CONTEXT` to a local checkout or reviewed upstream ref.
This avoids tagging a local build as the registry release.

```bash
docker compose --env-file voicebox/.env -f voicebox/docker-compose.yml -f voicebox/docker-compose.build.yml build
docker compose --env-file voicebox/.env -f voicebox/docker-compose.yml -f voicebox/docker-compose.build.yml up -d
```

Use both files for subsequent local-image operations; the overlay sets `pull_policy: never`. For Portainer, build/load the image on its target host, include the overlay,
and leave **Re-pull image** disabled: forced pulling may override service policy in
some versions. Do not use the registry update procedure for a local-only image.

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

- Registry pulls include application dependencies, not runtime model weights; initial model downloads can take time. Optional source builds also build the frontend and install Python/TTS dependencies.
- Model downloads are persisted under `/app/data/cache/huggingface` in the main `stacksmith_voicebox_data` volume.
- If CUDA out-of-memory errors appear, reduce the vLLM GPU reservation and/or Voicebox memory pressure before blaming Voicebox itself.
