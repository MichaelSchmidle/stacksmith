#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${VLLM_MODEL:-}" ]]; then
  echo "VLLM_MODEL must be set" >&2
  exit 1
fi

if [[ -n "${VLLM_PRELAUNCH_PIP_PACKAGES:-}" ]]; then
  # Temporary workaround for current Spark-friendly nightly images missing pandas.
  python3 -m pip install -q ${VLLM_PRELAUNCH_PIP_PACKAGES}
fi

args=(
  serve "${VLLM_MODEL}"
  --host 0.0.0.0
  --port 8000
  --gpu-memory-utilization "${VLLM_GPU_MEMORY_UTILIZATION:-0.70}"
  --max-model-len "${VLLM_MAX_MODEL_LEN:-8192}"
)

if [[ -n "${VLLM_SERVED_MODEL_NAME:-}" ]]; then
  args+=(--served-model-name "${VLLM_SERVED_MODEL_NAME}")
fi

if [[ -n "${VLLM_QUANTIZATION:-}" ]]; then
  args+=(--quantization "${VLLM_QUANTIZATION}")
fi

if [[ -n "${VLLM_API_KEY:-}" ]]; then
  args+=(--api-key "${VLLM_API_KEY}")
fi

if [[ -n "${VLLM_EXTRA_ARGS:-}" ]]; then
  # Intentionally allow shell-style splitting for additional vLLM flags.
  # shellcheck disable=SC2206
  extra_args=(${VLLM_EXTRA_ARGS})
  args+=("${extra_args[@]}")
fi

exec vllm "${args[@]}"
