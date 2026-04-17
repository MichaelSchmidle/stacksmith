# vLLM Inference Runtime

Internal model-serving runtime for GPU-backed inference hosts.

This service is intentionally **runtime-only**. It serves one model at a time and is designed to sit behind a stable frontend such as LiteLLM.

## What this stack is for

- Serve one primary chat or embedding model at a time
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
- `VLLM_GPU_MEMORY_UTILIZATION` - start conservative (`0.70` is a good default on new GPU/runtime combinations)
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

## Notes

- The compose file currently pins a CUDA 13 nightly image that is useful on newer NVIDIA systems. If you need a different image/tag for your hardware/runtime, change the compose file to match the rest of the repo's style
- The runtime bootstrap now lives directly in the container entrypoint, so Git/Portainer deployments do not depend on a fragile single-file script bind mount
- The bootstrap is implemented as a tiny inline Python launcher rather than bash, to avoid Compose/Portainer interpolation problems with `${...}` shell syntax
- At the moment, this stack can optionally apply small startup hotfix packages (for example `pandas`) if a chosen image is missing a runtime dependency on first launch
- When upstream images no longer need that workaround, set `VLLM_PRELAUNCH_PIP_PACKAGES=` to disable it

## Operating Model

This stack is best when treated as **one deployed model at a time**, not a model zoo.

For a few curated go-to models, change the env file and redeploy. Use LiteLLM in front if you want a stable client endpoint while the underlying model changes.
