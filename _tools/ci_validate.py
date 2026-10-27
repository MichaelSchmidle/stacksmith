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


def validate_sure_contract() -> None:
    stack = ROOT / "sure"
    compose = stack / "docker-compose.yml"
    required = {
        "SURE_HOSTNAME": "finance.example.com",
        "SURE_SECRET_KEY_BASE": "ci-placeholder",
        "SURE_DB_PASSWORD": "ci-placeholder",
        "ACTIVE_RECORD_ENCRYPTION_PRIMARY_KEY": "p" * 32,
        "ACTIVE_RECORD_ENCRYPTION_DETERMINISTIC_KEY": "d" * 32,
        "ACTIVE_RECORD_ENCRYPTION_KEY_DERIVATION_SALT": "s" * 32,
    }
    encryption_keys = {key for key in required if key.startswith("ACTIVE_RECORD_ENCRYPTION_")}
    template = (stack / ".env.example").read_text().splitlines()
    for key in encryption_keys:
        assert f"{key}=" in template, f"missing blank encryption key in env template: {key}"

    def render(**overrides: str | None) -> subprocess.CompletedProcess:
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("SURE_", "ACTIVE_RECORD_ENCRYPTION_"))
               and key not in ("COMPOSE_FILE", "COMPOSE_ENV_FILES")}
        env.update(required)
        for key, value in overrides.items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value
        return subprocess.run(
            ["docker", "compose", "--env-file", os.devnull, "-f", str(compose),
             "config", "--format", "json"],
            cwd=ROOT, env=env, text=True, capture_output=True,
        )

    result = render()
    assert result.returncode == 0, result.stderr
    config = json.loads(result.stdout)
    services = config["services"]
    assert set(services) == {"sure", "sure-worker", "sure-db", "sure-redis"}
    for service in services.values():
        assert not service.get("ports")
        assert not service.get("privileged", False)
        assert not any("docker.sock" in mount["target"] for mount in service.get("volumes", []))
    for name in ("sure", "sure-worker"):
        service = services[name]
        assert service["image"] == "ghcr.io/we-promise/sure:stable"
        env = service["environment"]
        assert env["APP_URL"] == "https://finance.example.com"
        assert env["RAILS_ASSUME_SSL"] == "true"
        assert env["RAILS_FORCE_SSL"] == "false"
        assert env["MCP_API_TOKEN"] == "" and env["MCP_USER_EMAIL"] == ""
        for key in encryption_keys:
            assert env.get(key) == required[key], f"{name} must receive explicit {key}"
        assert not any(key in env for key in ("OPENAI_ACCESS_TOKEN", "ANTHROPIC_API_KEY"))
    for name in ("sure-db", "sure-redis"):
        assert encryption_keys.isdisjoint(services[name].get("environment", {}))
    assert services["sure-worker"]["depends_on"]["sure"]["condition"] == "service_healthy"
    assert config["networks"]["sure-backend"]["internal"] is True
    assert set(services["sure-db"]["networks"]) == {"sure-backend"}
    assert set(services["sure-redis"]["networks"]) == {"sure-backend"}
    assert "stacksmith" not in services["sure-worker"]["networks"]
    assert services["sure"]["labels"]["traefik.http.routers.sure.entrypoints"] == "websecure-tailscale"
    assert services["sure"]["labels"]["traefik.docker.network"] == "stacksmith"
    for name in ("storage", "db", "redis"):
        assert config["volumes"][f"sure-{name}"]["name"] == f"stacksmith_sure_{name}"

    enabled = render(SURE_MCP_API_TOKEN="ci-mcp-placeholder", SURE_MCP_USER_EMAIL="agent@example.com")
    assert enabled.returncode == 0, enabled.stderr
    for name in ("sure", "sure-worker"):
        env = json.loads(enabled.stdout)["services"][name]["environment"]
        assert env["MCP_API_TOKEN"] == "ci-mcp-placeholder"
        assert env["MCP_USER_EMAIL"] == "agent@example.com"
    for key in required:
        for missing in (None, ""):
            failed = render(**{key: missing})
            assert failed.returncode != 0 and key in failed.stderr, f"must reject empty/missing {key}"
    for missing in (None, ""):
        failed = render(**{key: missing for key in encryption_keys})
        assert failed.returncode != 0 and any(key in failed.stderr for key in encryption_keys)
    print("sure: private routing, storage, MCP opt-in, stable images and fail-closed secrets/encryption: OK")


def validate_buzz_storage_contract() -> None:
    """Fence the S3 backend wiring, persistent metadata and admission defaults."""
    stack = ROOT / "buzz"
    required = required_env([stack / "docker-compose.yml"])
    required.update(BUZZ_HOSTNAME="buzz.example.com", BUZZ_S3_ACCESS_KEY="ci-access",
                    BUZZ_S3_SECRET_KEY="ci-secret", BUZZ_S3_BUCKET="ci-bucket")

    def render(example: bool = False, /, **overrides: str | None) -> subprocess.CompletedProcess:
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("BUZZ_", "COMPOSE_"))}
        env.update(required)
        for key, value in overrides.items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value
        return subprocess.run(
            ["docker", "compose", "--env-file", str(stack / ".env.example") if example else os.devnull,
             "-f", str(stack / "docker-compose.yml"), "config", "--format", "json"],
            cwd=ROOT, env=env, text=True, capture_output=True,
        )

    for example in (False, True):
        result = render(example)
        result.check_returncode()
        config = json.loads(result.stdout)
        services = config["services"]
        assert set(services) == {"buzz-relay", "buzz-pair-relay", "buzz-postgres", "buzz-redis", "buzz-seaweedfs"}
        relay = services["buzz-relay"]
        store = services["buzz-seaweedfs"]
        assert store["image"] == "chrislusf/seaweedfs:latest"
        assert store["command"][0] == "mini"
        for flag in ("-dir=/data", "-ip=buzz-seaweedfs", "-master.telemetry=false",
                     "-admin.ui=false", "-webdav=false", "-s3.port.iceberg=0", "-s3.port.lance=0",
                     "-s3.allowDeleteBucketNotEmpty=false", "-s3.autoCreateBucket=false"):
            assert flag in store["command"], flag
        assert not store.get("ports") and not store.get("labels")
        assert set(store["networks"]) == {"buzz-internal"}
        assert config["networks"]["buzz-internal"]["internal"] is True
        assert {(mount["source"], mount["target"]) for mount in store["volumes"]} == {
            ("buzz-seaweedfs-data", "/data"),
        }
        assert config["volumes"]["buzz-seaweedfs-data"]["name"] == "stacksmith_buzz_seaweedfs_data"
        assert "buzz-minio-data" not in config["volumes"]
        for key, name in (("AWS_ACCESS_KEY_ID", "BUZZ_S3_ACCESS_KEY"),
                          ("AWS_SECRET_ACCESS_KEY", "BUZZ_S3_SECRET_KEY"), ("S3_BUCKET", "BUZZ_S3_BUCKET")):
            assert store["environment"][key] == relay["environment"][name] == required[name]
        assert store["healthcheck"]["test"] == ["CMD", "wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8333/healthz"]
        assert relay["depends_on"]["buzz-seaweedfs"]["condition"] == "service_healthy"
        assert relay["environment"]["BUZZ_S3_ENDPOINT"] == "http://buzz-seaweedfs:8333"
        assert relay["environment"]["BUZZ_S3_ADDRESSING_STYLE"] == "path"
        assert relay["environment"]["BUZZ_GIT_CONFORMANCE_PROBE"] == "true"
        assert "BUZZ_GIT_PROBE_WRITERS" not in relay["environment"]
        assert "BUZZ_GIT_PROBE_ROUNDS" not in relay["environment"]
        assert relay["healthcheck"]["start_period"] == "3m0s"
        assert "/_readiness" in relay["healthcheck"]["test"][-1]
        for name in ("buzz-postgres-data", "buzz-redis-data", "buzz-git-data"):
            assert config["volumes"][name]["name"] == "stacksmith_" + name.replace("-", "_")
    for key in ("BUZZ_S3_ACCESS_KEY", "BUZZ_S3_SECRET_KEY"):
        for value in (None, ""):
            failed = render(**{key: value})
            assert failed.returncode != 0 and key in failed.stderr, (key, value)
    print("buzz: native S3 initialization, private storage, metadata persistence and unchanged probe: OK")


def validate_tallyport_contract() -> None:
    stack = ROOT / "tallyport"
    required = {
        "TALLYPORT_CONFIG_FILE": "/srv/tallyport/config.toml",
        "TALLYPORT_API_KEY_FILE": "/srv/tallyport/api-key",
        "TALLYPORT_INTAKE_DIR": "/srv/tallyport/intake",
        "TALLYPORT_STATE_DIR": "/srv/tallyport/state",
    }

    def render(**overrides: str | None) -> subprocess.CompletedProcess:
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("TALLYPORT_") and key != "COMPOSE_FILE"}
        env.update(required)
        for key, value in overrides.items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value
        return subprocess.run(
            ["docker", "compose", "--env-file", str(stack / ".env.example"),
             "-f", str(stack / "docker-compose.yml"), "config", "--format", "json"],
            cwd=ROOT, env=env, text=True, capture_output=True,
        )

    result = render()
    result.check_returncode()
    config = json.loads(result.stdout)
    assert set(config["services"]) == {"tallyport"}
    service = config["services"]["tallyport"]
    assert service["image"] == "ghcr.io/michaelschmidle/tallyport:latest"
    assert service["container_name"] == "stacksmith_tallyport"
    assert "build" not in service and not service.get("ports") and not service.get("labels")
    assert service["user"] == "10001:10001" and service["read_only"] is True
    assert service["cap_drop"] == ["ALL"]
    assert set(service["environment"]) == {"TZ"}
    assert "no-new-privileges:true" in service["security_opt"]
    assert service["command"] == ["watch"]
    assert float(service["cpus"]) == 0.5
    assert int(service["mem_limit"]) == 256 * 1024 * 1024
    assert int(service["pids_limit"]) == 64
    custom = render(TALLYPORT_CPU_LIMIT="1", TALLYPORT_MEMORY_LIMIT="512m",
                    TALLYPORT_PIDS_LIMIT="128")
    custom.check_returncode()
    limits = json.loads(custom.stdout)["services"]["tallyport"]
    assert float(limits["cpus"]) == 1
    assert int(limits["mem_limit"]) == 512 * 1024 * 1024
    assert int(limits["pids_limit"]) == 128
    mounts = {mount["target"]: mount for mount in service["volumes"]}
    assert set(mounts) == {"/config/config.toml", "/run/secrets/sure_api_key", "/intake", "/state"}
    for target, key in (("/config/config.toml", "TALLYPORT_CONFIG_FILE"),
                        ("/run/secrets/sure_api_key", "TALLYPORT_API_KEY_FILE"),
                        ("/intake", "TALLYPORT_INTAKE_DIR"), ("/state", "TALLYPORT_STATE_DIR")):
        mount = mounts[target]
        assert mount["type"] == "bind" and mount["source"] == required[key]
        assert mount.get("read_only", False) == (target not in ("/intake", "/state"))
        assert not mount.get("bind", {}).get("create_host_path", False)
    # Older Compose may omit false fields; retain a source-level fail-closed assertion.
    assert (stack / "docker-compose.yml").read_text().count("create_host_path: false") == 4
    assert set(service["networks"]) == {"default"}
    assert not config["networks"]["default"].get("external", False)
    for key in required:
        for value in (None, ""):
            failed = render(**{key: value})
            assert failed.returncode != 0 and key in failed.stderr, (key, value)
    print("tallyport: restricted binds, private prebuilt image, local state and no ingress: OK")


def main() -> None:
    validate_tallyport_contract()
    validate_buzz_storage_contract()
    validate_sure_contract()
    validate_nemotron_spark_contract()
    validate_nemotron_prebuild_runbook()
    validate_all_compose()
    validate_qwen_reasoning_aliases()
    validate_velogb10_token_budget()
    validate_voicebox_registry_contract()


if __name__ == "__main__":
    main()
