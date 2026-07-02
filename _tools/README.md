# Repository Tools

This directory contains helper scripts for developing, validating, and operating Stacksmith deployments.

Files in `_tools/` are **not service stacks**. They are not meant to be deployed by Portainer or included in Compose stack combinations. Top-level service directories remain the deployable Stacksmith units.

## Conventions

- Keep tools self-contained and safe to run from a cloned repository.
- Prefer deterministic output that can be compared across runs.
- Do not hard-code private hostnames, secrets, production paths, or machine-specific assumptions.
- Write generated results outside the repository, or keep them ignored if they are only local evidence.
- If a tool targets a specific stack, document the expected endpoint, model/service name, and required environment.

## Current tools

### `dgx_spark_benchmark.py`

Small OpenAI-compatible benchmark harness for DGX Spark / GB10 LLM serving tests.

Example:

```bash
python3 _tools/dgx_spark_benchmark.py \
  --base-url http://127.0.0.1:8000/v1 \
  --model qwen36-fast \
  --label current-vllm-qwen36 \
  --out-dir /tmp/stacksmith-dgx-benchmarks
```

The script writes JSON results and prints per-prompt throughput plus a summary. Use the same prompt set across candidate runtimes so comparisons stay meaningful.
