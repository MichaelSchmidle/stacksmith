# vLLM GB10 Qwen 3.6 Stack

Specialized DGX Spark / GB10 vLLM deployment for `AEON-7/Qwen3.6-35B-A3B-heretic-NVFP4` with the DFlash drafter.

This is intentionally **not** a generic vLLM template. It documents a hardware- and model-specific serving profile where the image, model layout, quantization settings, speculative drafter, and memory/context knobs are expected to move together.

## What this stack assumes

- Host: DGX Spark / GB10 with NVIDIA Container Toolkit.
- Model files already exist under the required `${QWEN36_MODELS_DIR}` host path:
  - `qwen36-nvfp4` → mounted as `/models/qwen36`
  - `qwen36-dflash` → mounted as `/models/qwen36-dflash`
- The service joins the external `stacksmith` network and is routed by Traefik.
- Defaults follow AEON's validated vLLM 0.23.0 profile for this exact GB10/model/drafter combination.

## Quick start

```bash
cp vllm-gb10-qwen-3.6/.env.example vllm-gb10-qwen-3.6/.env
# edit VLLM_HOSTNAME, QWEN36_MODELS_DIR, and memory/context settings

docker compose --env-file vllm-gb10-qwen-3.6/.env -f vllm-gb10-qwen-3.6/docker-compose.yml up -d
```

## Memory/context knobs

The defaults preserve the model's full context while leaving unified-memory headroom on GB10:

```bash
VLLM_GPU_MEMORY_UTILIZATION=0.70
VLLM_MAX_MODEL_LEN=262144
VLLM_MAX_NUM_SEQS=64
VLLM_MAX_NUM_BATCHED_TOKENS=65536
```

For co-hosting a larger second GPU workload, start with:

```bash
VLLM_GPU_MEMORY_UTILIZATION=0.65
VLLM_MAX_MODEL_LEN=131072
```

If the second workload still hits CUDA OOM during model load, reduce `VLLM_MAX_NUM_SEQS` before lowering memory utilization further.

## Runtime upgrade and rollback

The default image is pinned to AEON's validated vLLM 0.23.0 build:

```bash
QWEN36_VLLM_IMAGE=ghcr.io/aeon-7/aeon-vllm-ultimate:2026-06-18-v0.23.0-dflashfix
```

This supersedes `ghcr.io/aeon-7/vllm-spark-omni-q36:v1.2`. The model and quantization remain unchanged. DFlash uses 11 speculative tokens, and the obsolete `VLLM_TEST_FORCE_FP8_MARLIN=1` override is intentionally absent so the unified image can select its GB10 CUTLASS NVFP4 kernels.

If the local DFlash checkout predates 2026-04-19, refresh `z-lab/Qwen3.6-35B-A3B-DFlash` before deploying. Otherwise, keep the existing drafter to isolate the runtime change.

To roll back, set:

```bash
QWEN36_VLLM_IMAGE=ghcr.io/aeon-7/vllm-spark-omni-q36:v1.2
VLLM_SPECULATIVE_CONFIG={"method":"dflash","model":"/models/qwen36-dflash","num_speculative_tokens":15}
```

## Validation

```bash
curl -fsS https://qwen.yourdomain.com/health
curl -fsS https://qwen.yourdomain.com/v1/models | python3 -m json.tool
curl -fsS https://qwen.yourdomain.com/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen36-fast","messages":[{"role":"user","content":"What is 17 * 23? Answer with just the number."}],"max_tokens":64,"temperature":0,"chat_template_kwargs":{"enable_thinking":false}}'
```

Expected arithmetic answer: `391`.

## Notes

- `VLLM_SPECULATIVE_CONFIG` is passed through the container environment so JSON quoting survives Compose interpolation.
- DFlash depth 11 is AEON's validated optimum for this model; depth 15 wastes draft compute and degrades acceptance at long context.
- The unified image selects its GB10 CUTLASS NVFP4 kernels automatically; do not restore the old FP8-Marlin compatibility override.
- Container name is fixed as `stacksmith_vllm_gb10_qwen_3_6` to match Stacksmith naming conventions.
- vLLM listens on container port `8000`; Traefik routes to that fixed internal port.
