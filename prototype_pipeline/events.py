from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class PipelineLogger:
    def __init__(self, run: Path):
        self.run = run
        self.events_path = run / "output" / "pipeline_events.jsonl"
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        self.events_path.write_text("", encoding="utf-8")

    def event(self, kind: str, **payload: Any) -> None:
        record = {"timestamp": utc_now(), "kind": kind, **payload}
        with self.events_path.open("a", encoding="utf-8") as out:
            out.write(json.dumps(record, ensure_ascii=False) + "\n")

    def log(self, message: str, **payload: Any) -> None:
        print(f"[{utc_now()}] {message}", flush=True)
        self.event("log", message=message, **payload)


def call(args: list[str], *, root: Path, logger: PipelineLogger, required: bool = True, label: str | None = None) -> int:
    label = label or " ".join(args)
    logger.log(f"START {label}")
    logger.event("step_start", label=label, command=args)
    started = time.perf_counter()
    result = subprocess.run(args, cwd=root)
    duration = time.perf_counter() - started
    status = "passed" if result.returncode == 0 else "failed"
    logger.event(
        "step_end",
        label=label,
        command=args,
        status=status,
        returncode=result.returncode,
        duration_seconds=round(duration, 3),
    )
    logger.log(f"END {label}: {status} in {duration:.1f}s")
    if required and result.returncode != 0:
        raise SystemExit(result.returncode)
    return result.returncode
