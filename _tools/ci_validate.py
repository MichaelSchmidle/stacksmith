#!/usr/bin/env python3
"""Run Stacksmith's repository-specific CI checks."""

from __future__ import annotations

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
    if defaults["VELOGB10_DEFAULT_MAX_TOKENS"] + speculative_margin > defaults["VELOGB10_MAX_SEQ_LEN"]:
        raise AssertionError("veloGB10 default generation cap leaves no speculative-decoding headroom")
    print(f"velogb10 token budget: {defaults}: OK")


def main() -> None:
    validate_all_compose()
    validate_qwen_reasoning_aliases()
    validate_velogb10_token_budget()


if __name__ == "__main__":
    main()
