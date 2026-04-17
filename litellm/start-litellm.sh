#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${LITELLM_MASTER_KEY:-}" ]]; then
  echo "LITELLM_MASTER_KEY must be set" >&2
  exit 1
fi

if [[ -z "${LITELLM_UPSTREAM_MODEL:-}" ]]; then
  echo "LITELLM_UPSTREAM_MODEL must be set" >&2
  exit 1
fi

python3 - <<'PY'
import os
from pathlib import Path

model_alias = os.environ.get("LITELLM_MODEL_ALIAS", "primary-model")
upstream_model = os.environ["LITELLM_UPSTREAM_MODEL"]
vllm_api_base = os.environ.get("LITELLM_VLLM_API_BASE", "http://vllm:8000")
vllm_api_key = os.environ.get("LITELLM_VLLM_API_KEY", "placeholder")
supports_system_message = os.environ.get("LITELLM_SUPPORTS_SYSTEM_MESSAGE", "false").lower()
master_key = os.environ["LITELLM_MASTER_KEY"]

lines = [
    "model_list:",
    f"  - model_name: {model_alias}",
    "    litellm_params:",
    f"      model: hosted_vllm/{upstream_model}",
    f"      api_base: {vllm_api_base}",
    f"      api_key: {vllm_api_key}",
    f"      supports_system_message: {supports_system_message}",
]

embed_alias = os.environ.get("LITELLM_EMBED_ALIAS", "")
embed_upstream_model = os.environ.get("LITELLM_EMBED_UPSTREAM_MODEL", "")
embed_api_base = os.environ.get("LITELLM_EMBED_API_BASE", "")
if embed_alias and embed_upstream_model and embed_api_base:
    embed_api_key = os.environ.get("LITELLM_EMBED_API_KEY", "placeholder")
    lines.extend([
        f"  - model_name: {embed_alias}",
        "    litellm_params:",
        f"      model: hosted_vllm/{embed_upstream_model}",
        f"      api_base: {embed_api_base}",
        f"      api_key: {embed_api_key}",
        "      mode: embedding",
    ])

lines.extend([
    "general_settings:",
    f"  master_key: {master_key}",
])

Path('/tmp/litellm-config.yaml').write_text("\n".join(lines) + "\n")
PY

exec litellm --config /tmp/litellm-config.yaml --host 0.0.0.0 --port 4000
