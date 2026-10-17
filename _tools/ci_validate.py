#!/usr/bin/env python3
"""Run Stacksmith's repository-specific CI checks."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from jinja2 import Environment

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*):\?")


def required_env(files: list[Path]) -> dict[str, str]:
    names: set[str] = set()
    for path in files:
        names.update(REQUIRED_ENV_PATTERN.findall(path.read_text()))

    values: dict[str, str] = {}
    for name in names:
        if name.endswith(("_DIR", "_FILE", "_PATH")):
            values[name] = "/tmp/stacksmith-ci-placeholder"
        else:
            values[name] = "ci-placeholder"
    return values


def validate_compose(files: list[Path], env_file: Path, label: str) -> None:
    env = os.environ.copy()
    env.update(required_env(files))
    command = ["docker", "compose", "--env-file", str(env_file)]
    for path in files:
        command.extend(["-f", str(path)])
    command.extend(["config", "-q"])
    subprocess.run(command, cwd=ROOT, env=env, check=True)
    print(f"compose: {label}: OK")


def validate_all_compose() -> None:
    base_files = sorted(ROOT.glob("*/docker-compose.yml"))
    root_compose = ROOT / "docker-compose.yml"
    if root_compose.exists():
        base_files.insert(0, root_compose)

    for compose_file in base_files:
        env_file = compose_file.parent / ".env.example"
        if not env_file.exists():
            raise FileNotFoundError(f"missing env template for {compose_file.relative_to(ROOT)}")
        validate_compose([compose_file], env_file, str(compose_file.relative_to(ROOT)))

    for overlay in sorted(ROOT.glob("*/docker-compose.*.yml")):
        base = overlay.parent / "docker-compose.yml"
        if not base.exists():
            raise FileNotFoundError(f"missing base Compose file for {overlay.relative_to(ROOT)}")
        validate_compose(
            [base, overlay],
            overlay.parent / ".env.example",
            f"{base.relative_to(ROOT)} + {overlay.name}",
        )


def render_qwen_template(effort: str | None = None, *, enabled: bool = True) -> str:
    template_path = ROOT / "sglang-gb10-qwen-3.8/chat-template-sglang.jinja"
    environment = Environment()

    def raise_exception(message: str) -> None:
        raise RuntimeError(message)

    environment.globals["raise_exception"] = raise_exception
    template = environment.from_string(template_path.read_text())
    parameters: dict[str, object] = {
        "messages": [{"role": "user", "content": "hi"}],
        "enable_thinking": enabled,
        "add_generation_prompt": True,
        "tools": None,
        "add_vision_id": False,
    }
    if effort is not None:
        parameters["reasoning_effort"] = effort
    return template.render(**parameters)


def rendered_tier(output: str) -> str:
    if "Reasoning effort is set to xhigh." in output:
        return "xhigh"
    if "Reasoning effort is set to low." in output:
        return "low"
    return "medium"


def validate_qwen_reasoning_aliases() -> None:
    expected = {
        "minimal": "low",
        "low": "low",
        "medium": "medium",
        "high": "medium",
        "xhigh": "xhigh",
        "max": "xhigh",
    }
    actual = {effort: rendered_tier(render_qwen_template(effort)) for effort in expected}
    if actual != expected:
        raise AssertionError(f"unexpected Qwen reasoning aliases: {actual}")
    if rendered_tier(render_qwen_template()) != "xhigh":
        raise AssertionError("omitted effort must retain Qwen's upstream xhigh default")
    if "<think>\n\n</think>" not in render_qwen_template("max", enabled=False):
        raise AssertionError("disabled thinking must render the non-thinking prefill")
    try:
        render_qwen_template("bogus")
    except RuntimeError as exc:
        if "Unexpected reasoning effort" not in str(exc):
            raise
    else:
        raise AssertionError("unsupported reasoning effort must fail")
    print(f"qwen aliases: {actual}: OK")


def validate_velogb10_token_budget() -> None:
    stack = ROOT / "velogb10-qwen-3.8"
    compose = (stack / "docker-compose.yml").read_text()
    env_values = {}
    for line in (stack / ".env.example").read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            env_values[key] = value

    defaults = {}
    for key in ("VELOGB10_MAX_SEQ_LEN", "VELOGB10_DEFAULT_MAX_TOKENS"):
        match = re.search(rf"\$\{{{key}:-(\d+)\}}", compose)
        if match is None:
            raise AssertionError(f"missing numeric Compose default for {key}")
        defaults[key] = int(match.group(1))
        if env_values.get(key) != match.group(1):
            raise AssertionError(f"{key} differs between Compose and .env.example")

    speculative_margin = 16
    default_output_tokens = defaults["VELOGB10_DEFAULT_MAX_TOKENS"]
    minimum_prompt_tokens = default_output_tokens
    required_tokens = default_output_tokens + minimum_prompt_tokens + speculative_margin
    if required_tokens > defaults["VELOGB10_MAX_SEQ_LEN"]:
        raise AssertionError(
            "veloGB10 default generation cap must leave an equally sized prompt budget "
            "plus the speculative-decoding margin"
        )
    print(f"velogb10 token budget: {defaults}: OK")


def validate_voicebox_registry_contract() -> None:
    stack = ROOT / "voicebox"
    registry_image = "ghcr.io/michaelschmidle/voicebox-container:latest"
    adapter_image = "ghcr.io/michaelschmidle/voicebox-openai-adapter:latest"

    def render(*, example: bool = False, overlay: bool = False, **overrides: str) -> dict:
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("VOICEBOX_") and key != "COMPOSE_FILE"}
        env.update(VOICEBOX_HOSTNAME="voicebox.example.com",
                   VOICEBOX_ADAPTER_API_KEY="ci-placeholder")
        env.update(overrides)
        command = ["docker", "compose", "--env-file",
                   str(stack / ".env.example") if example else os.devnull,
                   "-f", str(stack / "docker-compose.yml")]
        if overlay:
            command.extend(["-f", str(stack / "docker-compose.build.yml")])
        command.extend(["config", "--format", "json"])
        return json.loads(subprocess.check_output(command, cwd=ROOT, env=env, text=True))

    defaults = render()
    example = render(example=True)
    for config in (defaults, example):
        voicebox = config["services"]["voicebox"]
        assert voicebox["image"] == registry_image
        assert voicebox.get("pull_policy") != "never"
        assert "build" not in voicebox
        assert voicebox["healthcheck"]["test"][1] == "python"
        assert config["services"]["voicebox-openai-adapter"]["image"] == adapter_image
        assert {(v["source"], v["target"]) for v in voicebox["volumes"]} == {
            ("voicebox-data", "/app/data"),
            ("voicebox-generations", "/app/data/generations"),
        }
        assert config["volumes"]["voicebox-data"]["name"] == "stacksmith_voicebox_data"
        assert config["volumes"]["voicebox-generations"]["name"] == "stacksmith_voicebox_generations"

    custom = render(example=True, VOICEBOX_IMAGE="example.com/voicebox:custom",
                    VOICEBOX_ADAPTER_IMAGE="example.com/adapter:custom",
                    VOICEBOX_CPU_LIMIT="2", VOICEBOX_MEMORY_LIMIT="8G")
    assert custom["services"]["voicebox"]["image"] == "example.com/voicebox:custom"
    assert custom["services"]["voicebox-openai-adapter"]["image"] == "example.com/adapter:custom"
    limits = custom["services"]["voicebox"]["deploy"]["resources"]["limits"]
    assert float(limits["cpus"]) == 2
    assert int(limits["memory"]) == 8589934592
    for example_mode in (False, True):
        local = render(example=example_mode, overlay=True, VOICEBOX_IMAGE="stacksmith_voicebox:latest",
                       VOICEBOX_BUILD_CONTEXT="https://github.com/jamiepine/voicebox.git#main")
        assert local["services"]["voicebox"]["image"] == "stacksmith_voicebox:latest"
        assert local["services"]["voicebox"]["pull_policy"] == "never"
        assert local["services"]["voicebox"]["build"]["context"] == "https://github.com/jamiepine/voicebox.git#main"
    print("voicebox registry defaults, overrides, storage and local build: OK")


def validate_nemotron_spark_contract() -> None:
    stack = ROOT / "sglang-gb10-nemotron-3.5-super-vl"
    required = {
        "NEMOTRON_HOSTNAME": "nemotron.example.com",
        "NEMOTRON_API_KEY": "ci-placeholder",
        "NEMOTRON_MODELS_DIR": "/srv/nemotron-super-vl",
    }

    def render(example: bool = False, /, **overrides: str | None) -> subprocess.CompletedProcess:
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("NEMOTRON_") and key != "COMPOSE_FILE"}
        env.update(required)
        for key, value in overrides.items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value
        return subprocess.run(
            ["docker", "compose", "--env-file",
             str(stack / ".env.example") if example else os.devnull,
             "-f", str(stack / "docker-compose.yml"), "config", "--format", "json"],
            cwd=ROOT, env=env, text=True, capture_output=True,
        )

    def config(*, example: bool = False, **overrides: str) -> dict:
        result = render(example, **overrides)
        result.check_returncode()
        return json.loads(result.stdout)

    for example in (False, True):
        rendered = config(example=example)
        service = rendered["services"]["nemotron"]
        args = service["command"]
        expected = {
            "--model-path": "/models/nvfp4",
            "--speculative-draft-model-path": "/models/lilicorr",
            "--speculative-algorithm": "DFLASH",
            "--served-model-name": "nemotron-3.5-super-vl",
            "--reasoning-parser": "nemotron_3",
            "--tool-call-parser": "qwen3_coder",
            "--kv-cache-dtype": "fp8_e4m3",
            "--mamba-backend": "flashinfer",
            "--mamba-ssm-dtype": "float16",
            "--mamba-cache-philox-rounds": "5",
            "--mamba-radix-cache-strategy": "extra_buffer",
            "--max-running-requests": "1",
            "--context-length": "32768",
            "--mem-fraction-static": "0.80",
            "--api-key": required["NEMOTRON_API_KEY"],
            "--port": "8000",
        }
        for flag, value in expected.items():
            assert args[args.index(flag) + 1] == value, (flag, args)
        assert "--trust-remote-code" in args
        assert "--enable-mamba-cache-stochastic-rounding" in args
        assert json.loads(args[args.index("--limit-mm-data-per-request") + 1]) == {
            "image": 1, "video": 0, "audio": 0,
        }
        assert service["image"] == "lmsysorg/sglang:nemotron3-5-super"
        assert service["platform"] == "linux/arm64"
        assert not any(key in service for key in ("ports", "network_mode", "build", "privileged", "ipc"))
        assert set(service["networks"]) == {"stacksmith"}
        assert rendered["networks"]["stacksmith"]["external"] is True
        binds = [v for v in service["volumes"] if v["type"] == "bind"]
        assert {(v["source"], v["target"]) for v in binds} == {
            (required["NEMOTRON_MODELS_DIR"] + "/nvfp4", "/models/nvfp4"),
            (required["NEMOTRON_MODELS_DIR"] + "/lilicorr", "/models/lilicorr"),
        }
        # Older Compose releases omit false fields from JSON. Keep the explicit
        # source setting as well as checking the normalized effective value.
        source = (stack / "docker-compose.yml").read_text()
        assert source.count("create_host_path: false") == len(binds) == 2
        assert all(v["read_only"] and v.get("bind", {}).get("create_host_path", False) is False
                   for v in binds)
        assert service["environment"]["HF_HUB_OFFLINE"] == "1"
        assert service["environment"]["TRANSFORMERS_OFFLINE"] == "1"
        assert service["environment"].get("MAX_JOBS") == "2", "Nemotron JIT compilation must be capped at two jobs"
        assert service["environment"].get("SGLANG_CACHE_DIR") == "/cache/sglang", "SGLang caches must use the persistent volume"
        assert service["environment"].get("FLASHINFER_WORKSPACE_BASE") == "/cache/sglang", "Prebuild and runtime must resolve the same FlashInfer workspace"
        assert any(v["type"] == "volume" and v["source"] == "nemotron-cache" and v["target"] == "/cache"
                   for v in service["volumes"])
        assert rendered["volumes"]["nemotron-cache"]["name"] == "stacksmith_sglang_gb10_nemotron_3_5_super_vl_cache"
        assert int(service["mem_limit"]) == int(service["memswap_limit"]) == 112 * 1024**3
        assert service["restart"] == "no"
        assert service["deploy"]["resources"]["reservations"]["devices"] == [
            {"driver": "nvidia", "count": 1, "capabilities": ["gpu"]},
        ]
        labels = service["labels"]
        router = "traefik.http.routers.sglang-gb10-nemotron-3-5-super-vl"
        assert labels[router + ".entrypoints"] == "websecure-tailscale"
        assert labels[router + ".rule"] == "Host(`nemotron.example.com`)"

    for key in required:
        for value in (None, ""):
            failed = render(**{key: value})
            assert failed.returncode != 0 and key in failed.stderr, (key, value, failed)
    custom = config(NEMOTRON_CONTEXT_LENGTH="16384", NEMOTRON_MEM_FRACTION_STATIC="0.75", MAX_JOBS="64",
                    SGLANG_CACHE_DIR="/outside-volume", FLASHINFER_WORKSPACE_BASE="/different-workspace")
    custom_env = custom["services"]["nemotron"]["environment"]
    assert custom_env["MAX_JOBS"] == "2"
    assert custom_env["SGLANG_CACHE_DIR"] == custom_env["FLASHINFER_WORKSPACE_BASE"] == "/cache/sglang"
    args = custom["services"]["nemotron"]["command"]
    assert args[args.index("--context-length") + 1] == "16384"
    assert args[args.index("--mem-fraction-static") + 1] == "0.75"
    print("nemotron Spark recipe, fail-closed inputs, offline mounts and private routing: OK")


def validate_nemotron_prebuild_shell(shell: str) -> None:
    """Execute the published shell with Docker stubbed; never contact a daemon."""
    import sys
    import tempfile

    volume = "stacksmith_sglang_gb10_nemotron_3_5_super_vl_cache"
    assert f"CACHE_VOLUME={volume}" in shell
    with tempfile.TemporaryDirectory(prefix="nemotron-runbook-") as directory:
        root = Path(directory)
        docker = root / "docker"
        docker.write_text(f"#!{sys.executable}\n" + '''import json
import os
import sys

args = sys.argv[1:]
with open(os.environ["DOCKER_CALL_LOG"], "a") as log:
    log.write(json.dumps(args) + "\\n")
scenario = os.environ["DOCKER_SCENARIO"]
volume = "stacksmith_sglang_gb10_nemotron_3_5_super_vl_cache"
if args[:2] == ["volume", "inspect"]:
    assert args[2:] == ["--format", '{{index .Labels "com.docker.compose.volume"}}', volume], args
    if scenario == "missing-volume":
        sys.exit(1)
    print("wrong-cache" if scenario == "wrong-label" else "nemotron-cache")
elif args[:1] == ["ps"]:
    assert "volume=" + volume in args, args
    if scenario == "ps-error":
        sys.exit(1)
    if scenario == "busy":
        print("running-server")
elif args[:2] == ["image", "inspect"]:
    if scenario == "image-error":
        sys.exit(1)
    print("sha256:runbook-test")
elif args[:1] == ["run"]:
    assert "type=volume,src=" + volume + ",dst=/cache" in args, args
    assert "sha256:runbook-test" in args, args
    if scenario == "build-error":
        sys.exit(1)
else:
    raise AssertionError(args)
''')
        docker.chmod(0o755)
        for scenario in ("success", "missing-volume", "wrong-label", "busy",
                         "ps-error", "image-error", "build-error"):
            log = root / (scenario + ".jsonl")
            env = dict(os.environ, PATH=str(root) + os.pathsep + os.environ["PATH"],
                       DOCKER_CALL_LOG=str(log), DOCKER_SCENARIO=scenario)
            # Model pasting into a non-strict parent shell. Failure must return
            # control without exiting it, leaking strict options or variables.
            script = ('set +e +u\nunset CACHE_VOLUME IMAGE\n' + shell +
                      '\nstatus=$?\nprintf "PARENT_SURVIVED %s\\n" "$status"\n'
                      '[[ $- != *e* && $- != *u* && ! -v CACHE_VOLUME && ! -v IMAGE ]]')
            result = subprocess.run(["bash", "-c", script], env=env,
                                    text=True, capture_output=True)
            assert result.returncode == 0, (scenario, result)
            assert ("PARENT_SURVIVED 0" in result.stdout) == (scenario == "success"), (scenario, result)
            assert "PARENT_SURVIVED " in result.stdout, (scenario, result)
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            ran = any(args[0] == "run" for args in calls)
            assert ran == (scenario in ("success", "build-error")), (scenario, calls)
            if scenario == "busy":
                assert "running" in result.stderr.lower(), result
            if scenario == "wrong-label":
                assert "label" in result.stderr.lower(), result
    print("nemotron runbook: fixed volume, idle-cache guard and parent-shell isolation: OK")


def validate_nemotron_prebuild_runbook() -> None:
    """Exercise the published Python snippet without CUDA, weights or compilation."""
    import contextlib
    import io
    import sys
    import types
    from unittest.mock import patch

    readme = (ROOT / "sglang-gb10-nemotron-3.5-super-vl/README.md").read_text()
    section = readme.split("## Persistent kernel caches and weights-unloaded prebuild\n", 1)[1]
    shell = section.split("```bash\n", 1)[1].split("\n```", 1)[0]
    subprocess.run(["bash", "-n"], input=shell, text=True, check=True)
    assert "--network none" in shell and "--read-only" in shell
    assert "--mount \"type=volume,src=$CACHE_VOLUME,dst=/cache\"" in shell
    assert "--memory 32g --memory-swap 32g" in shell
    assert "--gpus" not in shell and "/models" not in shell and "NEMOTRON_API_KEY" not in shell
    validate_nemotron_prebuild_shell(shell)
    source = shell.split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    code = compile(source, "README prebuild snippet", "exec")

    for failure in (None, "compile", "artifact", "workspace"):
        calls = []
        artifact = Path("/outside-volume" if failure == "workspace" else
                        "/cache/sglang/.cache/flashinfer/test/121a/cached_ops/fused_moe_120/fused_moe_120.so")

        def redirect() -> None:
            calls.append("redirect")

        def build(*, verbose: bool, need_lock: bool) -> None:
            assert verbose is True and need_lock is True
            calls.append("build")
            if failure == "compile":
                raise RuntimeError("injected compiler failure")

        def generate(*, use_fast_build: bool):
            assert calls == ["redirect"] and use_fast_build is False
            calls.append("generate")
            return types.SimpleNamespace(name="fused_moe_120", jit_library_path=artifact, build=build)

        names = ("sglang", "sglang.srt", "sglang.srt.environ", "flashinfer", "flashinfer.jit", "flashinfer.jit.fused_moe")
        modules = {name: types.ModuleType(name) for name in names}
        setattr(modules["sglang.srt.environ"], "redirect_third_party_caches", redirect)
        setattr(modules["flashinfer.jit.fused_moe"], "gen_cutlass_fused_moe_sm120_module", generate)
        output = io.StringIO()
        with patch.dict(sys.modules, modules), patch.object(Path, "is_file", return_value=failure != "artifact"), contextlib.redirect_stdout(output):
            try:
                exec(code, {})
            except (AssertionError, RuntimeError):
                if failure is None:
                    raise
            else:
                assert failure is None, f"prebuild must fail closed on {failure}"
        assert ("PREBUILD_ARTIFACT" in output.getvalue()) == (failure is None)
        assert calls == (["redirect", "generate"] if failure == "workspace" else ["redirect", "generate", "build"])
    print("nemotron runbook: shell syntax and mocked build-only success/failure paths: OK")


def main() -> None:
    validate_nemotron_spark_contract()
    validate_nemotron_prebuild_runbook()
    validate_all_compose()
    validate_qwen_reasoning_aliases()
    validate_velogb10_token_budget()
    validate_voicebox_registry_contract()


if __name__ == "__main__":
    main()
