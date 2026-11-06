# VoiceStudio — ARM64 NVIDIA CUDA

A browser-based local voice workbench using the official
[VoiceStudio](https://github.com/debpalash/VoiceStudio) image. This bundle is
specifically for Linux ARM64 NVIDIA servers such as DGX Spark / GB10, GH200 and
GB200, **not** x86-64, Apple Silicon Docker or Jetson/JetPack.

Stacksmith manages the application, GPU access, HTTPS routing and storage.
Use Studio's model catalogue to download supported models **on the server**;
downloading or switching a supported model does not require editing Compose,
rebuilding an image or replacing the container. This is a separate application,
not a frontend for an existing Qwen3-TTS or OpenAI-compatible inference service.

## Prerequisites

- ARM64 Linux Docker host with an NVIDIA GPU, NVIDIA Container Toolkit and a
  driver supporting CUDA 12.9 (the upstream ARM64 image uses PyTorch 2.8).
- Docker Compose with NVIDIA device reservations; use a **Docker Standalone**
  Portainer environment, not Docker Swarm (`docker stack deploy`).
- The external `stacksmith` network and an existing Traefik deployment on the
  same host, with `websecure-tailscale`, the `stacksmith` certificate resolver
  and `secure-headers@docker` middleware.
- A DNS hostname pointing to that host's Tailscale address, with the needed
  tailnet access and certificate/DNS challenge configuration already in place.
- Enough disk space for the application image, selected model weights and saved
  audio; multiple models can consume tens of GB. Check host/GPU headroom before
  loading models alongside other inference services.

## Configure and deploy

From this directory:

```bash
cp .env.example .env
chmod 600 .env
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
# Save the generated secret as VOICESTUDIO_API_KEY in .env; set the hostname too.
docker compose --env-file .env config --quiet
docker compose --env-file .env pull
docker compose --env-file .env up -d
```

The blank example API key deliberately prevents deployment until configured.
Do not print the fully rendered configuration: it contains the key.

For Portainer's Git deployment, select this repository and
`voicestudio-cuda-arm64/docker-compose.yml`, then enter the variables from
`.env.example` into the stack environment. No local build context or custom
image is needed. A repository change does not itself configure Portainer's
pull/redeployment schedule.

Open `https://<VOICESTUDIO_HOSTNAME>` and enter the administrator API key when
prompted. Studio exchanges it for a short-lived browser session; restarting the
backend invalidates that session, so keep the key in your password manager.
Use the model catalogue to choose a supported engine/model and follow its
licence/access prompts. Hugging Face downloads require outbound internet access;
a gated model may also require accepting its terms and entering an HF token in
Studio. The volume includes the encrypted token and must be treated as private.

### Image channel and engine limits

`ghcr.io/debpalash/voicestudio:cuda-arm64` is the native ARM64 **rolling main
preview**, equivalent to upstream `latest`; the unqualified `latest` image is
AMD64-only. This follows Stacksmith's rolling-image policy without emulation or
a maintained custom build. It can move ahead of stable releases and introduce
breaking changes. Upstream also publishes `stable-cuda-arm64` and exact release
variants for operators deliberately choosing a different update channel.

The catalogue is not a promise that every engine works in this image:

- Upstream documents GPU support for PyTorch engines such as OmniVoice and
  CosyVoice on ARM64 NVIDIA servers.
- CTranslate2-based faster-whisper and WhisperX are unavailable in the ARM64
  image because their cuDNN 8 dependency is missing; use `pytorch-whisper` for
  GPU transcription.
- Apple-only MLX adapters are not a Linux CUDA route. Native desktop controls
  and managed sidecar installation are not generally available through the
  remote browser; do not assume a listed engine can be installed there.

VoiceStudio is AGPL-3.0; **model licences are separate**. In particular,
OmniVoice's default weights have non-commercial terms. Pro does not remove
third-party licence restrictions. Read the upstream
[licence notice](https://github.com/debpalash/VoiceStudio/blob/main/LICENSE-NOTICE.md)
and the chosen model's terms before use.

## Security and persistence

- No host ports are published. Traefik routes UI, API, media and WebSockets on
  the same HTTPS origin via `websecure-tailscale` only. Do not add a public
  router, unencrypted port or in-app LAN-sharing listener.
- A nonempty administrator key is required by Compose. The UI shell and health
  route remain public **within the private network**; API/admin access needs
  authentication. The key grants powerful administration: treat Studio as a
  trusted operator tool, not a multi-user isolation boundary.
- No trusted-network or host-loopback authentication exemptions are enabled.
  Uvicorn proxy-header rewriting is disabled so forged forwarded client IPs
  cannot turn a remote caller into a loopback caller. The inspected upstream
  application separately honours HTTPS `X-Forwarded-Proto` for secure session
  cookies and origin checks; Traefik preserves the Host and supplies that header.
  Do not enable wildcard forwarded-IP trust to fix a proxy problem.
- Analytics are disabled. Local inference is distinct from optional external
  integrations: do not configure cloud engines/services if local-only processing
  is required. Model downloads still contact their upstream repositories.
- The upstream image runs as root inside the container and has a writable
  application filesystem; no privileged mode, Docker socket or host-directory
  mounts are supplied. The shared `stacksmith` network is not an isolation
  boundary against other containers on that network.
- `stacksmith_voicestudio_data` mounts `/app/omnivoice_data`: database, voices,
  projects, settings and Hugging Face models all persist across container
  replacement. `HF_HOME` points into that volume, not `/root/.cache/huggingface`.
  Do not use `docker compose down -v` unless deliberately deleting those data.

CPU and memory ceilings default to 4 CPUs and 16 GiB and can be changed with
`VOICESTUDIO_CPU_LIMIT` / `VOICESTUDIO_MEMORY_LIMIT`. The memory ceiling applies
to container RAM, not a separately enforced GPU-VRAM quota; size it for the
chosen model and account for shared system/GPU memory on unified-memory hosts.

## Validation and first-use acceptance

Repository validation requires no running service or production credentials:

```bash
# Run from the repository root; Jinja2 and Docker Compose are required.
python3 _tools/ci_validate.py
```

That checks Compose rendering and the routing/auth/storage/GPU contract, **not**
application startup, audio quality or a GPU workload. Manifest inspection can
establish ARM64 publication, not that inference works on a particular GPU.

After a separately authorized deployment:

1. Confirm `docker compose ps` becomes healthy; startup `/health` can return
   503 while initialization continues. Check Studio's reported device and run
   its self-check. A visible GPU alone is not proof a workload uses it.
2. Verify an unauthenticated API request is denied, then sign in over HTTPS.
   Exercise a settings change, a media preview/download and live WebSocket
   progress; check that the browser session cookie is Secure and HttpOnly.
3. Download one supported model through the browser, create a disposable test
   voice/project and generate speech. Verify the selected engine actually uses
   the GPU; record latency and listen to the result rather than counting an
   HTTP success as audio-quality acceptance.
4. Replace the application container as during an update, **keeping the same
   data volume**, and sign in again. Confirm the model is still installed and
   the saved voice/project/settings remain. Generate again without downloading
   the weights. This is a one-time persistence test, not normal model switching.

GPU execution, browser authentication/routing and replacement persistence remain
unverified until those steps are exercised on a compatible host.

## Updates, backup and recovery

Before pulling a new rolling image, record the running version and immutable
image digest, stop the application and take a consistent backup of the entire
`stacksmith_voicestudio_data` volume to an operator-chosen private destination.
Keep the administrator key separately in your password manager. Stop any other
writers; a live SQLite file copy is not a consistent backup.

Then pull the new image and bring the stack up with the same environment and
volume. Repeat health, authenticated browser access and a short generation
check. Pulling a tag and configuring automated Portainer redeployment are
separate decisions; database migrations can make an image-only rollback unsafe.

For recovery, stop the application, retain the failed volume for investigation,
restore the complete backup into an empty replacement volume and use the
recorded pre-upgrade image digest. Attach it under the expected volume name
before starting. Verify models, voices/projects and generation before reopening
access. Never restore over a volume while its application is writing to it.

## Upstream references

- [Docker installation, ARM64 compatibility and storage](https://github.com/debpalash/VoiceStudio/blob/v0.5.7/docs/install/docker.md)
- [API authentication and server mode](https://github.com/debpalash/VoiceStudio/blob/v0.5.7/docs/api-auth.md)
- [Inspected rolling image source](https://github.com/debpalash/VoiceStudio/tree/12e6578b36499b7aaec6d8d25395f110db676683)

These references describe the inspected baseline; the rolling image can change.
