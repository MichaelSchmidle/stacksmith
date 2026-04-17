# vLLM Inference Runtime

Internal model-serving runtime for GPU-backed inference hosts such as `inf1-ein`.

This service is intentionally **runtime-only**. It serves one model at a time and is designed to sit behind a stable frontend such as LiteLLM.

## What this stack is for

- Serve one primary chat model on Sparky / `inf1-ein`
- Keep model/runtime selection env-driven
- Expose the OpenAI-compatible vLLM API locally on `127.0.0.1:${VLLM_HOST_PORT:-8000}` for testing
- Provide an internal Docker-network backend for the `litellm/` stack

## Environment Configuration

```bash
cp vllm/.env.example vllm/.env
```

Important settings:

- `VLLM_MODEL` - actual model to load
- `VLLM_SERVED_MODEL_NAME` - stable backend name exposed by vLLM
- `VLLM_QUANTIZATION` - leave empty for unquantized models, set to `modelopt` for NVIDIA NVFP4 checkpoints
- `VLLM_GPU_MEMORY_UTILIZATION` - start conservative on Spark (`0.70` is a good default)
- `HF_TOKEN` - optional but useful for higher Hugging Face rate limits

## Deployment

Deploy the runtime alone:

```bash
docker compose -f vllm/docker-compose.yml up -d
```

Deploy it together with Traefik + LiteLLM:

```bash
docker compose -f traefik/docker-compose.yml -f vllm/docker-compose.yml -f litellm/docker-compose.yml up -d
```

## Notes for DGX Spark / Blackwell

- Current Spark-friendly nightly image (`vllm/vllm-openai:cu130-nightly`) is a good fit for Blackwell support
- At the moment, this stack applies a small startup hotfix (`pandas`) because the nightly image currently misses that dependency on first launch
- When upstream fixes the image, set `VLLM_PRELAUNCH_PIP_PACKAGES=` to disable the hotfix

## Operating Model

This stack is best when treated as **one deployed model at a time**, not a model zoo.

For a few curated go-to models, change the env file and redeploy. Use LiteLLM in front if you want a stable client endpoint while the underlying model changes.
