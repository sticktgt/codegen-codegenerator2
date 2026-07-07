from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required. Install with: pip install pyyaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def to_words(raw: str, strip_prefixes: list[str] | None = None) -> list[str]:
    value = raw
    for prefix in strip_prefixes or []:
        if value.startswith(prefix):
            value = value[len(prefix):]
            break
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return [part for part in value.strip().split() if part]


def pascal_case(raw: str, strip_prefixes: list[str] | None = None) -> str:
    return "".join(part[:1].upper() + part[1:] for part in to_words(raw, strip_prefixes))


def snake_case(raw: str, strip_prefixes: list[str] | None = None) -> str:
    words = to_words(raw, strip_prefixes)
    return "_".join(w.lower() for w in words)


def render_path(template: str, element: dict[str, Any], strip_prefixes: list[str]) -> str:
    source = element.get("id") or element.get("name") or "item"
    resource = element.get("resource") or source
    values = {
        "PascalName": pascal_case(source, strip_prefixes),
        "snake_name": snake_case(source, strip_prefixes),
        "snake_resource": snake_case(resource, strip_prefixes),
        "id": source,
    }
    return template.format(**values)


def copytree_clean(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def run_cmd(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
