#!/usr/bin/env python3
"""Small OpenAI-compatible benchmark harness for DGX Spark LLM serving tests."""

from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROMPTS = [
    {
        "name": "short_reasoning",
        "max_tokens": 256,
        "messages": [
            {"role": "system", "content": "Answer concisely. Do not show hidden reasoning."},
            {"role": "user", "content": "A train leaves Zurich at 08:15 averaging 92 km/h. Another leaves Bern at 08:45 averaging 110 km/h on the same route, 125 km behind. Around what time does the second catch the first? Give the calculation briefly."},
        ],
    },
    {
        "name": "code_python",
        "max_tokens": 512,
        "messages": [
            {"role": "system", "content": "Write correct, minimal Python."},
            {"role": "user", "content": "Write a Python function that takes a list of log lines and returns the top 5 IP addresses by failed login count. Include a tiny example."},
        ],
    },
    {
        "name": "german_decision_summary",
        "max_tokens": 384,
        "messages": [
            {"role": "system", "content": "Antworte auf Deutsch, entscheidungsorientiert und knapp."},
            {"role": "user", "content": "Fasse zusammen: Wir können entweder die bestehende Plattform stabilisieren oder eine neue Lösung pilotieren. Das Team ist ausgelastet, aber der Supportdruck steigt. Welche Entscheidung empfiehlst du und unter welchen Bedingungen?"},
        ],
    },
    {
        "name": "long_context_synthesis",
        "max_tokens": 512,
        "messages": [
            {"role": "system", "content": "Synthesize accurately. Be brief."},
            {"role": "user", "content": "Compare these constraints and recommend an architecture: local-first app, occasional sync, multiple actors editing shared state, audit trail required, must work offline for hours, conflict resolution should be understandable to non-engineers."},
        ],
    },
    {
        "name": "simple_factual_control",
        "max_tokens": 64,
        "messages": [
            {"role": "user", "content": "What is 17 * 23? Answer with just the number."},
        ],
    },
]


def post_json(url: str, payload: dict, timeout: int) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e


def run_case(base_url: str, model: str, case: dict, timeout: int) -> dict:
    payload = {
        "model": model,
        "messages": case["messages"],
        "max_tokens": case["max_tokens"],
        "temperature": 0,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    start = time.perf_counter()
    data = post_json(f"{base_url.rstrip('/')}/chat/completions", payload, timeout)
    elapsed = time.perf_counter() - start
    choice = data.get("choices", [{}])[0]
    message = choice.get("message", {})
    content = message.get("content") or ""
    usage = data.get("usage") or {}
    completion_tokens = usage.get("completion_tokens") or 0
    prompt_tokens = usage.get("prompt_tokens") or 0
    return {
        "name": case["name"],
        "elapsed_s": round(elapsed, 3),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "tok_per_s": round(completion_tokens / elapsed, 2) if elapsed and completion_tokens else None,
        "finish_reason": choice.get("finish_reason"),
        "content_preview": content[:500],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--model", default="qwen36-fast")
    parser.add_argument("--label", required=True)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--out-dir", default="./benchmark-results")
    args = parser.parse_args()

    result = {
        "label": args.label,
        "model": args.model,
        "base_url": args.base_url,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "runs": [],
    }

    for run_idx in range(args.runs):
        run = {"run": run_idx + 1, "cases": []}
        for case in PROMPTS:
            item = run_case(args.base_url, args.model, case, args.timeout)
            print(f"{case['name']}: {item['completion_tokens']} tok in {item['elapsed_s']}s = {item['tok_per_s']} tok/s", flush=True)
            run["cases"].append(item)
        result["runs"].append(run)

    tok_rates = [c["tok_per_s"] for r in result["runs"] for c in r["cases"] if c["tok_per_s"] is not None]
    result["summary"] = {
        "mean_tok_per_s": round(statistics.mean(tok_rates), 2) if tok_rates else None,
        "median_tok_per_s": round(statistics.median(tok_rates), 2) if tok_rates else None,
        "cases": len(tok_rates),
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_label = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in args.label)
    out = out_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{safe_label}.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    print(json.dumps(result["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
