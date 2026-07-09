from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from common import write_json

NUMBER_RE = re.compile(r"[-+]?[0-9]*\.?[0-9]+")


def _clean_line(line: str) -> str:
    line = line.strip()
    if line.startswith("│"):
        line = line[1:]
    if line.endswith("│"):
        line = line[:-1]
    return line.strip()


def parse_human_number(value: str) -> float | int | None:
    raw = value.strip().replace(",", "")
    is_money = raw.startswith("$")
    raw = raw[1:] if is_money else raw
    multiplier = 1.0
    if raw.endswith(("K", "k")):
        multiplier = 1_000.0
        raw = raw[:-1]
    elif raw.endswith(("M", "m")):
        multiplier = 1_000_000.0
        raw = raw[:-1]
    elif raw.endswith(("B", "b")):
        multiplier = 1_000_000_000.0
        raw = raw[:-1]
    match = NUMBER_RE.search(raw)
    if not match:
        return None
    number = float(match.group(0)) * multiplier
    if is_money:
        return round(number, 6)
    if abs(number - round(number)) < 1e-9:
        return int(round(number))
    return number


def _metric_pair(line: str) -> tuple[str, Any] | None:
    clean = _clean_line(line)
    if not clean or clean.startswith(("┌", "├", "└", "─")):
        return None
    if clean.isupper():
        return None
    match = re.match(r"(.+?)\s+(\$?[-+]?[0-9][0-9.,]*(?:\.[0-9]+)?[KMBkmb]?)\s*$", clean)
    if not match:
        return None
    key = re.sub(r"\s+", "_", match.group(1).strip().lower())
    value = parse_human_number(match.group(2))
    return key, value


def parse_opencode_stats(text: str) -> dict[str, Any]:
    """Parse the human table printed by `opencode stats`.

    This is intentionally tolerant because OpenCode stats is human-oriented, not
    a stable machine API. The pipeline stores only phase deltas, not raw
    before/after snapshots, unless a caller chooses to keep them externally.
    """
    data: dict[str, Any] = {
        "overview": {},
        "tokens": {},
        "models": {},
        "tools": {},
        "raw_available": bool(text.strip()),
    }
    section: str | None = None
    current_model: str | None = None

    for raw_line in text.splitlines():
        clean = _clean_line(raw_line)
        if not clean:
            continue
        upper = clean.upper()
        if upper in {"OVERVIEW", "COST & TOKENS", "MODEL USAGE", "TOOL USAGE"}:
            section = upper
            current_model = None
            continue
        if clean.startswith(("┌", "├", "└", "─")):
            continue

        if section == "MODEL USAGE":
            if "/" in clean and not re.search(r"\s+\$?[-+]?[0-9]", clean):
                current_model = clean.strip()
                data["models"].setdefault(current_model, {})
                continue
            pair = _metric_pair(raw_line)
            if pair and current_model:
                key, value = pair
                data["models"][current_model][key] = value
            continue

        if section == "TOOL USAGE":
            tool_match = re.match(r"([A-Za-z_][A-Za-z0-9_-]*)\s+.*?\s+(\d+)\s+\(", clean)
            if tool_match:
                data["tools"][tool_match.group(1)] = int(tool_match.group(2))
            continue

        pair = _metric_pair(raw_line)
        if not pair:
            continue
        key, value = pair
        if section == "OVERVIEW":
            data["overview"][key] = value
        elif section == "COST & TOKENS":
            data["tokens"][key] = value

    return data


def _num(value: Any) -> float | int:
    return value if isinstance(value, (int, float)) else 0


def _delta_number(before: dict[str, Any], after: dict[str, Any], key: str) -> float | int:
    return _num(after.get(key)) - _num(before.get(key))


def _clamp_nonnegative(value: float | int, issues: list[dict[str, Any]], *, path: str) -> float | int:
    if value < 0:
        issues.append({"path": path, "raw_value": value, "normalized_value": 0})
        return 0
    return value


def _metric_quality(issues: list[dict[str, Any]]) -> dict[str, Any]:
    if not issues:
        return {"status": "ok", "issues": []}
    return {
        "status": "unreliable",
        "issues": issues,
        "message": (
            "OpenCode stats before/after returned negative deltas. "
            "This can happen when the human-oriented stats window is reset, compacted, or affected by other sessions. "
            "Negative counters were normalized to 0 for reports; treat usage as approximate."
        ),
    }


def _model_delta(before_models: dict[str, Any], after_models: dict[str, Any], issues: list[dict[str, Any]]) -> dict[str, Any]:
    models: dict[str, Any] = {}
    for model in sorted(set(before_models) | set(after_models)):
        before = before_models.get(model, {}) or {}
        after = after_models.get(model, {}) or {}
        item = {
            "messages": _clamp_nonnegative(_delta_number(before, after, "messages"), issues, path=f"model_usage.{model}.messages"),
            "input_tokens": _clamp_nonnegative(_delta_number(before, after, "input_tokens"), issues, path=f"model_usage.{model}.input_tokens"),
            "output_tokens": _clamp_nonnegative(_delta_number(before, after, "output_tokens"), issues, path=f"model_usage.{model}.output_tokens"),
            "cache_read": _clamp_nonnegative(_delta_number(before, after, "cache_read"), issues, path=f"model_usage.{model}.cache_read"),
            "cache_write": _clamp_nonnegative(_delta_number(before, after, "cache_write"), issues, path=f"model_usage.{model}.cache_write"),
            "cost": _clamp_nonnegative(_delta_number(before, after, "cost"), issues, path=f"model_usage.{model}.cost"),
        }
        item["total_tokens"] = item["input_tokens"] + item["output_tokens"]
        models[model] = item
    return models


def _tools_delta(before_tools: dict[str, Any], after_tools: dict[str, Any], issues: list[dict[str, Any]]) -> dict[str, int]:
    return {
        tool: int(_clamp_nonnegative(_delta_number(before_tools, after_tools, tool), issues, path=f"tool_usage.{tool}"))
        for tool in sorted(set(before_tools) | set(after_tools))
    }


def compute_usage_delta(before: dict[str, Any], after: dict[str, Any], *, phase: str | None = None) -> dict[str, Any]:
    quality_issues: list[dict[str, Any]] = []
    models = _model_delta(before.get("models", {}) or {}, after.get("models", {}) or {}, quality_issues)
    tools = _tools_delta(before.get("tools", {}) or {}, after.get("tools", {}) or {}, quality_issues)

    input_tokens = sum(_num(item.get("input_tokens")) for item in models.values())
    output_tokens = sum(_num(item.get("output_tokens")) for item in models.values())
    cache_read = sum(_num(item.get("cache_read")) for item in models.values())
    cache_write = sum(_num(item.get("cache_write")) for item in models.values())
    cost = sum(_num(item.get("cost")) for item in models.values())
    model_messages = sum(_num(item.get("messages")) for item in models.values())

    # Fallback to aggregate COST & TOKENS if model rows are unavailable.
    if not models:
        tokens_before = before.get("tokens", {}) or {}
        tokens_after = after.get("tokens", {}) or {}
        input_tokens = _clamp_nonnegative(_delta_number(tokens_before, tokens_after, "input"), quality_issues, path="llm_usage.input_tokens")
        output_tokens = _clamp_nonnegative(_delta_number(tokens_before, tokens_after, "output"), quality_issues, path="llm_usage.output_tokens")
        cache_read = _clamp_nonnegative(_delta_number(tokens_before, tokens_after, "cache_read"), quality_issues, path="llm_usage.cache_read")
        cache_write = _clamp_nonnegative(_delta_number(tokens_before, tokens_after, "cache_write"), quality_issues, path="llm_usage.cache_write")
        cost = _clamp_nonnegative(_delta_number(tokens_before, tokens_after, "total_cost"), quality_issues, path="llm_usage.cost")

    overview_before = before.get("overview", {}) or {}
    overview_after = after.get("overview", {}) or {}
    messages = _clamp_nonnegative(_delta_number(overview_before, overview_after, "messages"), quality_issues, path="llm_usage.messages_delta")
    sessions = _clamp_nonnegative(_delta_number(overview_before, overview_after, "sessions"), quality_issues, path="llm_usage.sessions_delta")

    delta = {
        "phase": phase,
        "source": "opencode stats before/after",
        "llm_usage": {
            "sessions_delta": sessions,
            "messages_delta": messages,
            "model_messages_delta": model_messages,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cache_read": cache_read,
            "cache_write": cache_write,
            "cost": round(float(cost), 6),
        },
        "model_usage": models,
        "tool_usage": tools,
        "quality": _metric_quality(quality_issues),
        "notes": [
            "Delta is reliable only when no other OpenCode sessions run concurrently.",
            "messages_delta is a proxy for LLM interaction count; raw provider call count may differ.",
        ],
    }
    if quality_issues:
        delta["notes"].append("Negative OpenCode stats deltas were normalized to 0; usage for this phase is approximate.")
    return delta

def collect_stats(days: int = 1, models: int = 10) -> tuple[str, dict[str, Any]]:
    if shutil.which("opencode") is None:
        text = ""
        parsed = {"status": "skipped", "reason": "opencode CLI not found in PATH"}
        return text, parsed
    result = subprocess.run(
        ["opencode", "stats", "--days", str(days), "--models", str(models)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    text = result.stdout
    parsed = parse_opencode_stats(text)
    parsed["command"] = f"opencode stats --days {days} --models {models}"
    parsed["returncode"] = result.returncode
    if result.stderr:
        parsed["stderr"] = result.stderr
    return text, parsed


def write_usage_delta(run: Path, phase: str, before: dict[str, Any], after: dict[str, Any], *, duration_seconds: float | None = None, requested_model: str | None = None) -> Path:
    delta = compute_usage_delta(before, after, phase=phase)
    if duration_seconds is not None:
        delta["duration_seconds"] = round(duration_seconds, 3)
    if requested_model:
        delta["requested_model"] = requested_model
    out = run / "usage" / f"{phase}.delta.json"
    write_json(out, delta)
    return out


# Backward-compatible snapshot helpers for manual debugging.
def snapshot(run: Path, phase: str, label: str, *, days: int = 1, models: int = 10) -> Path:
    usage_dir = run / "usage"
    usage_dir.mkdir(parents=True, exist_ok=True)
    text, parsed = collect_stats(days=days, models=models)
    text_path = usage_dir / f"{phase}.{label}.txt"
    json_path = usage_dir / f"{phase}.{label}.json"
    text_path.write_text(text, encoding="utf-8")
    write_json(json_path, parsed)
    return json_path


def write_delta(run: Path, phase: str) -> Path:
    before_path = run / "usage" / f"{phase}.before.json"
    after_path = run / "usage" / f"{phase}.after.json"
    if not before_path.exists() or not after_path.exists():
        raise FileNotFoundError(f"Need both {before_path} and {after_path}")
    before = json.loads(before_path.read_text(encoding="utf-8"))
    after = json.loads(after_path.read_text(encoding="utf-8"))
    return write_usage_delta(run, phase, before, after)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--label", choices=["before", "after"], help="Write a stats snapshot")
    parser.add_argument("--delta", action="store_true", help="Compute delta from before/after snapshots")
    parser.add_argument("--days", type=int, default=1)
    parser.add_argument("--models", type=int, default=10)
    args = parser.parse_args()

    if args.label:
        path = snapshot(args.run, args.phase, args.label, days=args.days, models=args.models)
        print(path)
    if args.delta:
        path = write_delta(args.run, args.phase)
        print(path)


if __name__ == "__main__":
    main()
