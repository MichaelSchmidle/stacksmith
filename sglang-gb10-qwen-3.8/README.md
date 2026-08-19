# SGLang GB10 Qwen 3.8 Stack

Specialized single-model DGX Spark / GB10 stack for `Qwen3.8-27B` using the RadixArk NVFP4 target, DSpark speculative drafter, and SGLang.

This stack is deliberately separate from `vllm-gb10-qwen-3.6/`. Keep that stack and its model files for rollback; do not run both inference engines concurrently on one GB10.

## Profile

- Native context: **262,144 tokens per request**.
- Target: `RadixArk/Qwen3.8-27B-NVFP4`.
- Drafter: `RadixArk/Qwen3.8-27B-DSpark`.
- Runtime image: pinned `lmsysorg/sglang:qwen38-27b` digest validated by the community recipe on 2026-08-15.
- Exposure: authenticated Bearer-token API through Stacksmith's Tailscale-only Traefik entrypoint; no host port is published.
- Host protection: 100 GB container cap and `--mem-fraction-static 0.50`.

The model's YaRN recipe can reach 1M tokens with MTP, but YaRN and DSpark are incompatible in this pinned SGLang build. This stack therefore fixes context at the maximum validated native DSpark length instead of exposing a broken context knob.

## Prerequisites

- DGX Spark / GB10 with stock NVIDIA drivers, Docker, and NVIDIA Container Toolkit.
- External Docker network `stacksmith` and a compatible Traefik deployment.
- About 24 GB for the two checkpoints plus space for the 39 GB runtime image and compile cache.
- The host reserved for this inference engine while it runs. Competing GPU or unified-memory workloads can cause OOMs or host instability.

## Prepare pinned checkpoints

Download the exact revisions into the directory that will become `QWEN38_MODELS_DIR`:

```bash
mkdir -p /srv/qwen38

hf download RadixArk/Qwen3.8-27B-NVFP4 \
  --revision 52d1adc5f38aa5ebf099c29ed7025ba34cfbb854 \
  --local-dir /srv/qwen38/qwen38-nvfp4

hf download RadixArk/Qwen3.8-27B-DSpark \
  --revision 923ed3a8572615643f0137e424e4ce4edd7f1cda \
  --local-dir /srv/qwen38/qwen38-dspark
```

`chat-template-sglang.jinja` is the target checkpoint's pinned template with the community recipe's two agent-client compatibility changes: OpenAI/Claude reasoning-effort aliases and mid-conversation system reminders. It remains covered by the checkpoint's Apache-2.0 license in `LICENSE.chat-template`. Refresh and review both whenever the target checkpoint changes.

## Deploy

```bash
cp sglang-gb10-qwen-3.8/.env.example sglang-gb10-qwen-3.8/.env
# Set SGLANG_HOSTNAME, QWEN38_MODELS_DIR, and a random SGLANG_API_KEY.

# Stop any competing inference stack first.
docker compose --env-file vllm-gb10-qwen-3.6/.env \
  -f vllm-gb10-qwen-3.6/docker-compose.yml down

docker compose --env-file sglang-gb10-qwen-3.8/.env \
  -f sglang-gb10-qwen-3.8/docker-compose.yml up -d
```

The first boot can take about 9–15 minutes while SGLang compiles kernels and captures CUDA graphs. The named compile-cache volume survives container replacement.

## Validate

```bash
docker compose --env-file sglang-gb10-qwen-3.8/.env \
  -f sglang-gb10-qwen-3.8/docker-compose.yml ps
docker compose --env-file sglang-gb10-qwen-3.8/.env \
  -f sglang-gb10-qwen-3.8/docker-compose.yml logs -f sglang

curl https://qwen.example.com/health
curl -H "Authorization: Bearer ${SGLANG_API_KEY}" \
  https://qwen.example.com/v1/models
```

The OpenAI-compatible base URL is `https://qwen.example.com/v1`; the served model defaults to `qwen3.8-27b`. Clients must send `Authorization: Bearer <SGLANG_API_KEY>`. SGLang also exposes its authenticated Anthropic-compatible `/v1/messages` endpoint.

## Memory and context safety

Do **not** raise `SGLANG_MEM_FRACTION_STATIC` above `0.50` on GB10 unified memory. SGLang does not account for all transient FlashInfer and CUDA-graph allocations; higher values have caused hard host freezes.

The defaults provide a shared FP8 KV pool of roughly 386K tokens, enough for one full 262K request plus concurrent shorter requests. `SGLANG_MAX_MAMBA_CACHE_SIZE=96` and `SGLANG_MAX_RUNNING_REQUESTS=8` are a validated pair. Change them only after measuring real concurrency and memory behavior.

## Update and rollback

The image digest, target revision, draft revision, and chat template form one tested unit. Upgrade them together on a branch, then repeat long-context and Hermes tool-use benchmarks before deployment.

Rollback is operationally simple because the Qwen3.6 stack is unchanged:

```bash
docker compose --env-file sglang-gb10-qwen-3.8/.env \
  -f sglang-gb10-qwen-3.8/docker-compose.yml down

docker compose --env-file vllm-gb10-qwen-3.6/.env \
  -f vllm-gb10-qwen-3.6/docker-compose.yml up -d
```

The two stacks use different containers, model directories, and cache volumes.

## Sources

- [Pinned single-Spark SGLang + NVFP4 + DSpark recipe](https://github.com/hasso5703/dgx-spark-qwen38/tree/4a9025045e53d56558c1f57355e1ca866651e533)
- [SGLang Qwen3.8 cookbook](https://docs.sglang.io/cookbook/autoregressive/Qwen/Qwen3.8-27B)
- [RadixArk NVFP4 target](https://huggingface.co/RadixArk/Qwen3.8-27B-NVFP4)
- [RadixArk DSpark drafter](https://huggingface.co/RadixArk/Qwen3.8-27B-DSpark)
