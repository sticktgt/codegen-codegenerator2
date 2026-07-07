from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunPaths:
    run: Path

    @property
    def workspace(self) -> Path:
        return self.run / "workspace"

    @property
    def input(self) -> Path:
        return self.run / "input"

    @property
    def output(self) -> Path:
        return self.run / "output"

    @property
    def logs(self) -> Path:
        return self.run / "logs"

    @property
    def usage(self) -> Path:
        return self.run / "usage"

    @property
    def agent_reports(self) -> Path:
        return self.run / "agent_reports"

    @property
    def dist(self) -> Path:
        return self.run / "dist"

    @property
    def workspace_input(self) -> Path:
        return self.workspace / "prototype" / "input"

    @property
    def workspace_output(self) -> Path:
        return self.workspace / "prototype" / "output"

    def workspace_rel(self, rel_path: str | Path) -> Path:
        return self.workspace / rel_path

    def output_file(self, name: str | Path) -> Path:
        return self.output / name


def project_root_from_module(module_file: str | Path) -> Path:
    return Path(module_file).resolve().parents[2]
