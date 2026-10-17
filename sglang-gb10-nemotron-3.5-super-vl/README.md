# SGLang GB10 Nemotron 3.5 Super VL

Single-DGX-Spark / GB10 candidate stack for NVIDIA's **120B-A12B NVFP4 vision-language model**, with its **LiLiCorr** speculative drafter. This is separate from the Qwen stacks: no existing model files, containers, client aliases or routes are replaced.

**Status: prepared for later commissioning, not GPU-runtime validated.** Compose validation and an ARM64 registry manifest establish packaging, not successful model loading, memory fit, inference quality or speed. Do not run another large inference server alongside this one.

## Profile and upstream basis

- Runtime: `lmsysorg/sglang:nemotron3-5-super`, NVIDIA's model-specific SGLang image. This is a justified exception to the repository's generic `latest` preference: the launch recipe requires specialized model/kernel support. The tag can still move; record the pulled digest before each trial.
- Target: `nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-NVFP4`, revision `59b8721646c38111a242da18218859fb2b454322`.
- Drafter: `nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-NVFP4-LiLiCorr`, revision `292bf1efc06ba39567da7351f2ad7a522afa3959`.
- Based on NVIDIA's Spark recipe: DFLASH/LiLiCorr, FP8 KV cache, FlashInfer attention/Mamba, `extra_buffer` radix cache, one running request, `nemotron_3` reasoning and `qwen3_coder` tool parsing. **Compatibility correction:** this stack uses **FP16** Mamba state with stochastic rounding and five Philox rounds. The pinned model-card recipe says BF16 plus stochastic rounding, but the image's advertised [Mamba validation code](https://github.com/sgl-project/sglang/blob/2c7511f6f7/python/sglang/srt/arg_groups/mamba_hook.py) rejects that pair and requires `float16`. The correction passes that source validation branch; it still needs GPU inference/quality validation.
- Initial local limits: **32,768 tokens** shared between input, image tokens and output; one image per request; video/audio disabled; 2,048-token prefill chunks. The model's advertised 1M context is **not** the deployed limit.
- OpenAI-compatible base URL: `https://nemotron.example.com/v1`; model ID: `nemotron-3.5-super-vl`.

The context/prefill/multimodal limits and `0.80` static-memory fraction are commissioning choices, not NVIDIA performance or memory-fit measurements. The 112 GiB container cap, equal swap limit, and private 16 GiB shared-memory allocation are guardrails, **not a guarantee against unified-memory pressure or host freezes**. Shared memory consumes the container budget; GPU allocations are not necessarily fully contained by cgroup accounting. Do not copy the smaller Qwen stack's `0.50` fraction: this target's weights alone exceed that pool. Stop the trial if host headroom deteriorates; do not keep increasing allocation to chase startup success.

`MAX_JOBS=2` caps the Ninja build parallelism used by FlashInfer and SGLang JIT compilation. The inspected runtime reads this variable in both build paths; without it, Ninja chooses its own parallelism. This limits concurrent build jobs, **not** total CPU threads, GPU workspace or host memory. First-start compilation/autotuning can peak above the memory used by loaded weights and KV pools. Continue monitoring host memory and stop if headroom deteriorates: the cap is a bounded commissioning change, not a demonstrated fix for startup memory pressure. It does not disable autotuning or change the context, memory ceiling or model recipe.

`restart: "no"` deliberately prevents automatic restart loops and unattended boot-time GPU contention during commissioning. Revisit restart policy only after an accepted deployment; health status alone does not restart a failed container.

## Prerequisites and checkpoint preparation

- One Linux ARM64 DGX Spark / GB10 with a driver compatible with the image's CUDA 13.0 runtime, Docker Compose v2+ and NVIDIA Container Toolkit. Use a Portainer **Docker Standalone** endpoint, not Swarm.
- An external `stacksmith` Docker network and same-host Traefik using the Tailscale-only `websecure-tailscale` entrypoint, `stacksmith` certificate resolver and `secure-headers@docker` middleware. Configure DNS/TLS before commissioning. No host port or host networking is published by this stack.
- Check free disk/RAM and competing GPU workloads first. Weights occupy roughly 70 GiB plus 1.3 GiB for the drafter; also budget for the large unpacked runtime image, download scratch space and compile caches. Check actual free space before downloads rather than assuming model size is the whole requirement.
- Review the target and drafter's [OpenMDW-1.1 license](https://openmdw.ai/license/1-1/) before downloading. Both repositories are currently ungated. The runtime enables `trust_remote_code` for local checkpoint code: use the exact revisions below and review any update.

Run these **later, on the Docker endpoint**, using an installed Hugging Face CLI and a writable parent directory:

```bash
mkdir -p /srv/nemotron-super-vl
hf download nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-NVFP4 \
  --revision 59b8721646c38111a242da18218859fb2b454322 \
  --local-dir /srv/nemotron-super-vl/nvfp4
hf download nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-NVFP4-LiLiCorr \
  --revision 292bf1efc06ba39567da7351f2ad7a522afa3959 \
  --local-dir /srv/nemotron-super-vl/lilicorr
```

Download the complete repositories, including tokenizer, processor and Python code, not only weight shards. Both mounts are read-only with `create_host_path: false`. Runtime Hugging Face/Transformers offline modes prevent an accidental checkpoint download during startup; missing files must be repaired during preparation. No HF token is passed to the server.

## Persistent kernel caches and weights-unloaded prebuild

`SGLANG_CACHE_DIR=/cache/sglang` and `FLASHINFER_WORKSPACE_BASE=/cache/sglang` explicitly place SGLang's caches and FlashInfer's version/architecture-specific JIT workspace in the existing `nemotron-cache` volume. `XDG_CACHE_HOME` alone does not redirect these paths. SGLang also derives its third-party cache defaults from this base; the existing explicit Inductor path remains `/cache/inductor`.

For a cold build, prepare the expensive FlashInfer **`fused_moe_120`** module before loading model weights. This is a manual, one-shot compiler container, **not another serving service**. It mounts only the existing cache volume: no checkpoint directories, backend credentials, network or GPU access. It does not load the target/drafter or execute inference/autotuning. Other modules may still compile at server startup; this does not eliminate every runtime allocation or establish memory fit.

Stop/pause the serving stack and any competing large model server through Portainer first; verify the workflows stay paused. Do not build against a cache being used by a running server. Keep unrelated services running. On the Docker endpoint, use **Bash** and select the actual Portainer Compose project; discovery must yield exactly one existing cache volume, otherwise stop rather than silently create or warm the wrong volume:

```bash
set -eu
PROJECT=sglang-gb10-nemotron-3-5-super-vl # replace if the Portainer project differs
mapfile -t caches < <(docker volume ls \
  --filter "label=com.docker.compose.project=$PROJECT" \
  --filter label=com.docker.compose.volume=nemotron-cache --format '{{.Name}}')
test "${#caches[@]}" -eq 1
CACHE_VOLUME=${caches[0]}
docker volume inspect "$CACHE_VOLUME" >/dev/null
IMAGE=$(docker image inspect lmsysorg/sglang:nemotron3-5-super --format '{{.Id}}')
printf 'Prebuild image: %s; cache volume: %s\n' "$IMAGE" "$CACHE_VOLUME"

# Preserve the output externally; check the exit status before any server start.
# 32 GiB / four CPUs are bounds for this compiler-only example, not a measured
# successful full-build budget. Failure must not trigger an automatic retry.
docker run --rm -i --name stacksmith_nemotron_kernel_prebuild --pull=never \
  --network none --read-only --memory 32g --memory-swap 32g --cpus 4 \
  --tmpfs /tmp:rw,nosuid,nodev,size=4g \
  --mount "type=volume,src=$CACHE_VOLUME,dst=/cache" \
  -e MAX_JOBS=2 -e SGLANG_CACHE_DIR=/cache/sglang \
  -e FLASHINFER_WORKSPACE_BASE=/cache/sglang -e FLASHINFER_CUDA_ARCH_LIST=12.1a \
  -e TORCHINDUCTOR_CACHE_DIR=/cache/inductor \
  -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
  --entrypoint python3 "$IMAGE" -u - <<'PY'
from pathlib import Path
from sglang.srt.environ import redirect_third_party_caches

# Apply the same third-party defaults before importing FlashInfer.
redirect_third_party_caches()
from flashinfer.jit.fused_moe import gen_cutlass_fused_moe_sm120_module

spec = gen_cutlass_fused_moe_sm120_module(use_fast_build=False)
assert spec.name == "fused_moe_120"
assert spec.jit_library_path.is_relative_to(Path("/cache/sglang"))
spec.build(verbose=True, need_lock=True)
assert spec.jit_library_path.is_file(), "Compiler returned without its shared library"
print("PREBUILD_ARTIFACT", spec.jit_library_path, flush=True)
PY
```

`12.1a` is the GB10 compiler target; the generator's `sm120`/`fused_moe_120` name covers this SM12x path. Do not use fast-build flags or a different architecture/cache layout when expecting the server to reuse the artifact. The script calls the runtime's **build-only** API, not `build_and_load()` or a model launcher. A compiler failure leaves partial work in the cache for inspection; it is not permission to increase limits or start the server anyway.

After a successful build, recreate a disposable check container with the same image, cache mount and environment, and verify the reported artifact still exists at the resolved path. File persistence alone does **not** prove binary compatibility or GPU correctness: the next supervised server trial must verify it actually loads/reuses the module, completes warm-up and generates a response under the host-memory guard. Do not delete the volume during teardown (`down -v` would discard it).

Cache binaries are trusted executable input. Restrict cache-volume write access. Record the exact image ID and use it for both preparation and serving; do not pull the rolling tag between phases. Reassess/rebuild the cache when the image, compiler, driver or architecture changes rather than assuming the directory name proves compatibility. The source/path probe for this procedure used image ID `sha256:8d30c455e22629697a894933597367c48931a449ab37e5d3f89cf9e290c44d6b`; the full compilation, shared-library load and GPU startup remain commissioning gates.

## Configure and deploy later

For Portainer Git deployment, select this repository and Compose path **`sglang-gb10-nemotron-3.5-super-vl/docker-compose.yml`**. Enter the variables from `.env.example` in Portainer; Git deployments do not automatically load that example. Bind paths refer to the **Docker endpoint**, not the Portainer server. No auxiliary Git files or image build are required.

| Variable | Meaning |
| --- | --- |
| `NEMOTRON_HOSTNAME` | Required private routed hostname, without scheme or path |
| `NEMOTRON_API_KEY` | Required strong random Bearer token; blank fails validation |
| `NEMOTRON_MODELS_DIR` | Required absolute parent directory containing `nvfp4/` and `lilicorr/` |
| `NEMOTRON_CONTEXT_LENGTH` | Default `32768`; do not raise before measuring memory and long-context behaviour |
| `NEMOTRON_MEM_FRACTION_STATIC` | Default `0.80`; supervised memory tuning only |
| `TZ` | Default `Europe/Zurich` |

CLI alternative, from the repository root:

```bash
cp sglang-gb10-nemotron-3.5-super-vl/.env.example sglang-gb10-nemotron-3.5-super-vl/.env
# Fill in the three required values; keep this file private.
docker compose --env-file sglang-gb10-nemotron-3.5-super-vl/.env \
  -f sglang-gb10-nemotron-3.5-super-vl/docker-compose.yml config -q
docker compose --env-file sglang-gb10-nemotron-3.5-super-vl/.env \
  -f sglang-gb10-nemotron-3.5-super-vl/docker-compose.yml pull
# Stop the current model server through its owning Portainer stack before starting this one.
docker compose --env-file sglang-gb10-nemotron-3.5-super-vl/.env \
  -f sglang-gb10-nemotron-3.5-super-vl/docker-compose.yml up -d
```

Before the trial, record the current server's stack configuration, image identity, checkpoint paths, route and client alias so it can be restored unchanged. Use a distinct candidate hostname; do not switch LiteLLM aliases as part of stack creation. Watch startup logs and host memory throughout compilation/loading. The 20-minute healthcheck grace period is not a startup-time promise. A failed startup stays stopped for inspection.

## Commissioning checks

1. Inspect container logs/status and host memory. Capture startup logs in a protected file outside the container **before** a Portainer stop/recreate: teardown can remove the container and its Docker logs. Logs can contain the API key; redact them before sharing. Check for OOMs, missing kernels, unsupported arguments and checkpoint-loading errors. Verify LiLiCorr is actually enabled; an HTTP health response is insufficient.
2. Verify routed `/health`, then `/v1/models` **with** the configured Bearer token. `/v1/models` without a token must return HTTP 401. Health/readiness/metrics endpoints are intentionally unauthenticated in this SGLang build; keep the entire route private.
3. Exercise text, non-thinking mode, an actual local image and a complete tool-call/result round trip. Example below uses only Python's standard library, a small non-sensitive local image and explicit client environment variables. It does not read Portainer or deployment `.env` values.

```bash
# Set BASE_URL=https://nemotron.example.com/v1, NEMOTRON_API_KEY, and IMAGE_FILE
# in the client shell; IMAGE_FILE must name a small local PNG/JPEG.
python3 - <<'PY'
import base64
import json
import mimetypes
import os
from pathlib import Path
import urllib.request

base = os.environ['BASE_URL'].rstrip('/')
key = os.environ['NEMOTRON_API_KEY']
model = 'nemotron-3.5-super-vl'

def complete(messages, **extra):
    body = dict(model=model, messages=messages, temperature=1.0, top_p=0.95,
                max_tokens=1024, chat_template_kwargs={'enable_thinking': False})
    body.update(extra)
    request = urllib.request.Request(base + '/chat/completions',
        data=json.dumps(body).encode(),
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    with urllib.request.urlopen(request, timeout=300) as response:
        choice = json.load(response)['choices'][0]
    assert choice['finish_reason'] != 'length', 'Truncated: retry with an adequate output budget'
    return choice['message']

text = complete([{'role': 'user', 'content': 'Antworte auf Deutsch: Was ist ein guter Rollback-Plan?'}])
assert text.get('content'), text
print('TEXT:', text['content'])

path = Path(os.environ['IMAGE_FILE'])
mime = mimetypes.guess_type(path.name)[0]
assert mime in ('image/png', 'image/jpeg'), mime
url = 'data:' + mime + ';base64,' + base64.b64encode(path.read_bytes()).decode()
image = complete([{'role': 'user', 'content': [
    {'type': 'text', 'text': 'Describe this image and transcribe any visible text.'},
    {'type': 'image_url', 'image_url': {'url': url}},
]}])
assert image.get('content'), image
print('IMAGE:', image['content'])

tools = [{'type': 'function', 'function': {'name': 'lookup_stock',
    'description': 'Look up product stock.', 'parameters': {'type': 'object',
    'properties': {'product': {'type': 'string'}}, 'required': ['product']}}}]
messages = [{'role': 'user', 'content': 'Look up the stock for widget using the tool, then report the count.'}]
call_message = complete(messages, tools=tools,
    tool_choice={'type': 'function', 'function': {'name': 'lookup_stock'}})
calls = call_message.get('tool_calls') or []
assert len(calls) == 1 and calls[0]['function']['name'] == 'lookup_stock', call_message
assert json.loads(calls[0]['function']['arguments']) == {'product': 'widget'}, calls
messages += [call_message, {'role': 'tool', 'tool_call_id': calls[0]['id'],
                           'content': json.dumps({'product': 'widget', 'count': 7})}]
result = complete(messages, tools=tools, tool_choice='none')
assert result.get('content') and '7' in result['content'] and not result.get('tool_calls'), result
print('TOOL RESULT:', result['content'])
PY
```

4. Separately test `chat_template_kwargs: {"enable_thinking": true}` with an adequate output budget, inspect reasoning/content separation, and reject token-cap truncations. The non-thinking smoke probe is not a reasoning-quality test. Manually compare the image description/OCR with its actual contents; nonempty text is not visual accuracy.
5. Only then compare completed-task latency, streamed time to first token, German prose and tool reliability against the existing server on matching tasks. A positive structural smoke test is not a model-quality verdict. Clients must advertise the **deployed** context, not the native 1M window.

API keys are visible to endpoint administrators through container arguments; Docker/Portainer access is privileged. Shared-network peers can reach container port 8000, so Bearer authentication remains necessary even behind Tailscale. Do not publish this route publicly. No extra Linux capabilities, host IPC, privileged mode, host mounts beyond checkpoints or Docker socket access are requested.

## Updates, rollback and storage

- Updating Git does not itself authorize deployment. A merge adds a new optional stack; it does not create a Portainer stack. Image pulls and per-stack auto-update settings are separate operations. Keep automatic candidate redeployment disabled until commissioning is accepted.
- Before an update, record the running image ID/RepoDigest and checkpoint revisions. A moving tag is not a recoverable version identifier; retain the prior image locally. Repeat startup, text/image/tool and memory checks after changing the runtime or checkpoints.
- Roll back through Portainer: stop this candidate, restore/start the previously recorded model stack, then verify its authenticated model list and a real completion. Restore any deliberately changed client route separately. Never co-run the servers during handback.
- `stacksmith_sglang_gb10_nemotron_3_5_super_vl_cache` stores derived Hugging Face code and compilation caches; it survives container replacement and can be rebuilt while stopped. Checkpoints stay in the two host directories. Preserve configuration, revision records and any irreplaceable local model changes; base weights can be re-downloaded. Do not use `down -v` on unrelated stacks.

## Sources

- [NVIDIA target model card and exact recipe revision](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-NVFP4/blob/59b8721646c38111a242da18218859fb2b454322/README.md#sglang)
- [LiLiCorr checkpoint and license](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-NVFP4-LiLiCorr/tree/292bf1efc06ba39567da7351f2ad7a522afa3959)
- [SGLang source revision advertised by the ARM64 image](https://github.com/sgl-project/sglang/tree/2c7511f6f7)

Registry metadata checked during preparation: image index `sha256:4832ffd7d9c55e967c935f8835c613365daa812f9b06ff2ec6d7ecc139e9e573`, ARM64 child `sha256:d0465e2752740143668b8186a91b2a6eb8cc9014121d78afd54d37c276bd4277`, CUDA `13.0.3`. These are observed artifact identities, not deployment pins or a claim that the container has been run.
