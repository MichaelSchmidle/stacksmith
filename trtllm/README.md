# TensorRT-LLM Stack for Stacksmith

This is a Stacksmith-style service bundle for running NVIDIA's official TensorRT-LLM container on a DGX Spark. It keeps the Stacksmith directory structure while following NVIDIA's current single-node Spark guidance.

It is intentionally Spark-optimized rather than generic:

- runtime: NVIDIA's official `nvcr.io/nvidia/tensorrt-llm/release:1.2.0rc6`
- model handles: NVIDIA-curated DGX Spark models
- networking: host mode, matching NVIDIA's documented Spark path

The authoritative DGX Spark model lists are:

- [TensorRT-LLM for Spark](https://build.nvidia.com/spark/trt-llm/instructions)
- [vLLM for Spark](https://build.nvidia.com/spark/vllm/stacked-spark)

## Files

- `docker-compose.yml` - TensorRT-LLM service definition
- `.env.example` - environment template for model and runtime tuning

## Why host networking

Most Stacksmith services join the external `stacksmith` Docker network and are routed through Traefik. This one intentionally uses `network_mode: host` instead.

Reason:

- NVIDIA's DGX Spark playbook uses host networking for TensorRT-LLM.
- `trtllm-serve` clearly supports `--port`, but not a separate host bind flag in the current container help output.
- Host networking avoids binding ambiguity and matches the configuration that already worked on this machine.

That means this stack is best treated as a high-performance internal API service, not a Traefik-routed web app.

## Quick start

1. Copy the environment file:

```bash
cp trtllm/.env.example trtllm/.env
```

2. Edit `trtllm/.env`:

```bash
MODEL_HANDLE=nvidia/Qwen3-30B-A3B-FP4
HF_TOKEN=hf_your_token_here
TRTLLM_BIND_HOST=0.0.0.0
TRTLLM_PORT=8355
TRTLLM_MAX_BATCH_SIZE=64
TRTLLM_FREE_GPU_MEMORY_FRACTION=0.90
```

3. Start the stack:

```bash
docker compose --env-file trtllm/.env -f trtllm/docker-compose.yml up -d
```

4. Check readiness:

```bash
curl http://127.0.0.1:8355/v1/models
```

If you plan to connect from another machine, test the network-reachable address too:

```bash
curl http://your-host-or-tailscale-ip:8355/v1/models
```

5. Test a chat completion:

```bash
curl -s http://127.0.0.1:8355/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nvidia/Qwen3-30B-A3B-FP4",
    "messages": [{"role": "user", "content": "Write one sentence explaining what NVFP4 is."}],
    "max_tokens": 128
  }'
```

## Model selection

Change `MODEL_HANDLE` in `trtllm/.env` to switch runtimes without editing the compose file.

Good DGX Spark starting points from NVIDIA's curated matrix:

- [`nvidia/Qwen3-30B-A3B-FP4`](https://huggingface.co/nvidia/Qwen3-30B-A3B-FP4)
- [`nvidia/Gemma-4-31B-IT-NVFP4`](https://huggingface.co/nvidia/Gemma-4-31B-IT-NVFP4)
- [`nvidia/Llama-3.3-70B-Instruct-FP4`](https://huggingface.co/nvidia/Llama-3.3-70B-Instruct-FP4)

For the broader Spark-curated list, use NVIDIA's official matrices:

- [TensorRT-LLM DGX Spark model matrix](https://build.nvidia.com/spark/trt-llm/instructions)
- [vLLM DGX Spark model matrix](https://build.nvidia.com/spark/vllm/stacked-spark)

## Tuning knobs

- `TRTLLM_BIND_HOST` controls which interface the API binds to.
- `TRTLLM_PORT` controls the OpenAI-compatible API port on the host.
- `TRTLLM_MAX_BATCH_SIZE` controls `trtllm-serve --max_batch_size`.
- `TRTLLM_FREE_GPU_MEMORY_FRACTION` is written into the extra YAML config as `kv_cache_config.free_gpu_memory_fraction`.
- `TRT_LLM_DISABLE_LOAD_WEIGHTS_IN_PARALLEL=1` can help if DGX Spark hits weight-load memory pressure.
- `TRTLLM_SERVER_ARGS` lets you append raw extra flags to `trtllm-serve`.

## Single-Host And Dual-Host Use

Use the same stack in both cases. The only difference is which address clients use:

- Single-host: set `TRTLLM_BIND_HOST=0.0.0.0` or a specific local interface IP, then point local clients at that host IP or Tailscale IP.
- Dual-host: set `TRTLLM_BIND_HOST=0.0.0.0` or a specific LAN/Tailscale IP on the inference machine, then point the remote UI at that machine's reachable URL.

Avoid `127.0.0.1` if another machine or another bridged container needs to reach the inference API.

## Stacksmith usage

This service follows the normal Stacksmith directory layout, but because it uses host networking it is usually deployed on its own instead of being merged with `traefik/docker-compose.yml`.

```bash
docker compose --env-file trtllm/.env -f trtllm/docker-compose.yml up -d
```
