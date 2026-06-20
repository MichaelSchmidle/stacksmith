# vLLM GB10 Qwen 3.6 Stack

Specialized DGX Spark / GB10 vLLM deployment for `AEON-7/Qwen3.6-35B-A3B-heretic-NVFP4` with the DFlash drafter.

This is intentionally **not** a generic vLLM template. It documents a hardware- and model-specific serving profile where the image, model layout, quantization settings, speculative drafter, and memory/context knobs are expected to move together.

## What this stack assumes

- Host: DGX Spark / GB10 with NVIDIA Container Toolkit.
- Model files already exist under the required `${QWEN36_MODELS_DIR}` host path:
  - `qwen36-nvfp4` → mounted as `/models/qwen36`
  - `qwen36-dflash` → mounted as `/models/qwen36-dflash`
- The service joins the external `stacksmith` network and is routed by Traefik.
- Defaults prioritize a large-context standalone vLLM server.

## Quick start

```bash
cp vllm-gb10-qwen-3.6/.env.example vllm-gb10-qwen-3.6/.env
# edit VLLM_HOSTNAME, QWEN36_MODELS_DIR, and memory/context settings

docker compose --env-file vllm-gb10-qwen-3.6/.env -f vllm-gb10-qwen-3.6/docker-compose.yml up -d
```

## Memory/context knobs

The defaults prioritize one large vLLM server:

```bash
VLLM_GPU_MEMORY_UTILIZATION=0.85
VLLM_MAX_MODEL_LEN=262144
VLLM_MAX_NUM_SEQS=128
VLLM_MAX_NUM_BATCHED_TOKENS=65536
```

A high `VLLM_GPU_MEMORY_UTILIZATION` value lets vLLM reserve most available GPU memory for weights, CUDA graphs, and KV cache. For co-hosting Voicebox, start with:

```bash
VLLM_GPU_MEMORY_UTILIZATION=0.70
VLLM_MAX_MODEL_LEN=131072
```

If Voicebox still hits CUDA OOM during model load, lower further to `0.65` or reduce `VLLM_MAX_NUM_SEQS`.

## Validation

```bash
curl -fsS http://127.0.0.1:${VLLM_PORT:-8000}/health
curl -fsS http://127.0.0.1:${VLLM_PORT:-8000}/v1/models | python3 -m json.tool
curl -fsS http://127.0.0.1:${VLLM_PORT:-8000}/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen36-fast","messages":[{"role":"user","content":"What is 17 * 23? Answer with just the number."}],"max_tokens":64,"temperature":0,"chat_template_kwargs":{"enable_thinking":false}}'
```

Expected arithmetic answer: `391`.

## Notes

- `VLLM_SPECULATIVE_CONFIG` is passed through the container environment so JSON quoting survives Compose interpolation.
- `VLLM_TEST_FORCE_FP8_MARLIN=1` is intentional for the current NVFP4 MoE path on this image.
- Container name is fixed as `stacksmith_vllm_gb10_qwen_3_6` to match Stacksmith naming conventions.
