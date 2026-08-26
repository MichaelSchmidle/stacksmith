# veloGB10 Qwen 3.8 Canary Stack

Specialized single-node NVIDIA DGX Spark / GB10 canary for `Qwen3.8-27B` using the GB10-native [veloGB10](https://github.com/sf-stav/veloGB10) inference engine, its NVFP4 target, and DFlash 2 speculative decoding.

This stack is deliberately separate from `sglang-gb10-qwen-3.8/`. Do not run both inference engines concurrently on one GB10. Keep the SGLang stack and its model files unchanged for rollback.

## Pinned unit

- Engine release: [`veloGB10 v0.5.0`](https://github.com/sf-stav/veloGB10/releases/tag/v0.5.0), source commit `89242407e799930e9f4e51559bffc186033d90a7`.
- Release archive SHA-256: `1d0a564a1874febf34e011c35e6c2fd649239d5af8b838d3fdb41f942fb9b1c7`.
- Runtime base: NVIDIA CUDA 13.0.2 runtime on Ubuntu 24.04, pinned multi-architecture manifest digest.
- Target: [`doth4580/Qwen3.8-27B-NVFP4-FULL`](https://huggingface.co/doth4580/Qwen3.8-27B-NVFP4-FULL), revision `1b49c1e2ad0b7621e9a991bc4e2dd10380cfc175`.
- Drafter: [`doth4580/Qwen3.8-27B-DFlash2`](https://huggingface.co/doth4580/Qwen3.8-27B-DFlash2), revision `91a59627d8e504687daf82dd341d1e1dcf33671b`.
- License: engine, target, and drafter declare Apache-2.0 at these pinned revisions.
- Native context: 262,144 tokens; the canary defaults to one 65,536-token sequence to preserve unified-memory headroom.

The Dockerfile packages the upstream binary/PTX release; it does not compile or modify veloGB10 source. Build and model artifacts are not committed to Stacksmith.

## Important canary limitations

### No built-in authentication

veloGB10 v0.5.0 accepts requests without authentication and enables permissive CORS. This stack publishes no host port and applies a required Traefik source-IP allowlist. Restrict `VELOGB10_ALLOWED_SOURCE_RANGES` to the LiteLLM host and explicit canary clients; do not expose this route publicly.

This is an intentionally accepted operator trust boundary, not end-to-end authentication: containers already attached to the external `stacksmith` network can call Velo directly and bypass Traefik. A compromised or SSRF-capable sibling service could consume inference resources. Deploy only alongside services controlled by the same operator. Add an authenticated proxy and private backend network if that trust assumption does not hold.

After deployment, verify the client address Traefik actually observes. Same-host hairpin traffic may arrive from a Docker bridge address rather than the expected VPN address, so configure exact observed CIDRs instead of assuming the route source.

### Reasoning-effort compatibility

veloGB10 v0.5.0 currently maps an incoming OpenAI `reasoning_effort: high` to `no_think`. The container default is therefore pinned to `medium`, but a request field overrides it.

Before routing Hermes through LiteLLM, configure the Velo canary deployment to remove `reasoning_effort` from forwarded requests so the server default wins:

```yaml
model_list:
  - model_name: qwen38-velo
    litellm_params:
      model: openai/qwen3.8-27b-velo
      api_base: https://velo.example.com/v1
      additional_drop_params:
        - reasoning_effort
```

Verify the rendered behavior before use. Until that is done, benchmark clients must omit the field. Do not replace the production alias merely to try the canary.

### Runtime maturity

This is a new hardware-specific engine. v0.5.0 only recently added vision and repaired OpenAI multipart/tool-call behavior. Treat it as a bounded canary, not an unattended production replacement.

Keep `VELOGB10_DEFAULT_MAX_TOKENS` below `VELOGB10_MAX_SEQ_LEN`. In v0.5.0, a client that omits `max_tokens` inherits the server default; setting it equal to the context length leaves no room for speculative-decoding state and produces an empty `context_length_exceeded` response. The 8,192-token default leaves safe headroom for Open WebUI and Hermes requests.

## Prepare pinned checkpoints

```bash
mkdir -p /srv/velogb10-models

hf download doth4580/Qwen3.8-27B-NVFP4-FULL \
  --revision 1b49c1e2ad0b7621e9a991bc4e2dd10380cfc175 \
  --local-dir /srv/velogb10-models/qwen38-nvfp4-full

hf download doth4580/Qwen3.8-27B-DFlash2 \
  --revision 91a59627d8e504687daf82dd341d1e1dcf33671b \
  --local-dir /srv/velogb10-models/qwen38-dflash2
```

Both directories are mounted read-only. CUDA/runtime caches and Velo's MTP calibration use separate named volumes so restarts do not repeat calibration unnecessarily.

## Build the local runtime image

Upstream does not publish a container image. The base Compose stack therefore uses `pull_policy: never`: Portainer must find the tagged image in the target Docker engine's local image store and will not try Docker Hub.

After this stack is merged, build the packaging layer once on the ARM64 GB10 Docker host directly from the merged Stacksmith commit. This uses a transient remote Git build context and does not require a persistent second checkout:

```bash
STACKSMITH_REF=<merged-commit-sha>

docker build \
  --tag stacksmith_velogb10_qwen_3_8:0.5.0 \
  "https://github.com/MichaelSchmidle/stacksmith.git#${STACKSMITH_REF}:velogb10-qwen-3.8"
```

Verify that the image exists on the same Docker engine Portainer will deploy to:

```bash
docker image inspect stacksmith_velogb10_qwen_3_8:0.5.0 \
  --format 'architecture={{.Architecture}} revision={{index .Config.Labels "org.opencontainers.image.revision"}}'
```

For local development from an existing checkout, the build overlay remains available:

```bash
cp velogb10-qwen-3.8/.env.example velogb10-qwen-3.8/.env
# Set VELOGB10_HOSTNAME, VELOGB10_ALLOWED_SOURCE_RANGES, and VELOGB10_MODELS_DIR.

docker compose --env-file velogb10-qwen-3.8/.env \
  -f velogb10-qwen-3.8/docker-compose.yml \
  -f velogb10-qwen-3.8/docker-compose.build.yml \
  build
```

The Docker build verifies the upstream release archive and Apache-2.0 license checksums before producing the local image.

Build each new Velo version before changing or redeploying the Portainer stack. If the local image is pruned, rebuild the same pinned version before redeployment.

## Start the canary

Stop the competing SGLang model server first. For the first validation, stop other GPU model services too; reintroduce Voicebox only after Velo is healthy and memory headroom has been measured.

```bash
docker compose --env-file sglang-gb10-qwen-3.8/.env \
  -f sglang-gb10-qwen-3.8/docker-compose.yml down

docker compose --env-file velogb10-qwen-3.8/.env \
  -f velogb10-qwen-3.8/docker-compose.yml up -d
```

The first model load and DFlash calibration can take several minutes. Confirm readiness:

```bash
docker compose --env-file velogb10-qwen-3.8/.env \
  -f velogb10-qwen-3.8/docker-compose.yml ps

curl -fsS https://velo.example.com/health
curl -fsS https://velo.example.com/v1/models

docker stats --no-stream stacksmith_velogb10_qwen_3_8
free -h
```

`Authorization` headers are accepted but ignored by veloGB10. The routed endpoint relies on the source-IP allowlist; direct access from the shared Docker network relies on the documented operator trust boundary.

## Canary gates

Compare against the current SGLang baseline using the same fixed harness:

1. C1 latency, TTFT, visible tok/s, and total reasoning-token use.
2. German FCL-style administrative prompts and instruction following.
3. Hermes skill selection and multi-step tool calls, streaming and non-streaming.
4. Long multi-turn sessions with prefix-cache reuse.
5. Context-length rejection and completion truncation behavior.
6. Stability and unified-memory pressure first in isolation, then with Voicebox restored.

Coding throughput is not an upgrade criterion for this deployment. Promote only if operational reliability is intact and interactive speed improves materially.

## Update and rollback

Treat the CUDA base digest, veloGB10 version/archive checksum, source commit/license checksum, target revision, and drafter revision as one tested unit. Update them together on a branch; `VELOGB10_VERSION` also changes the local image tag. Retain the previous image, rebuild, and repeat the canary gates.

The upstream v0.5.0 tag and release artifacts are not cryptographically signed. The pinned SHA-256 values provide integrity checking, not publisher attestation; that is accepted for this bounded canary.

Rollback:

```bash
docker compose --env-file velogb10-qwen-3.8/.env \
  -f velogb10-qwen-3.8/docker-compose.yml down

docker compose --env-file sglang-gb10-qwen-3.8/.env \
  -f sglang-gb10-qwen-3.8/docker-compose.yml up -d
```

No volumes or model directories are shared with the production SGLang stack.
