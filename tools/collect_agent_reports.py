from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from common import write_json

REPORT_NAMES = [
    "plan_proposal.json",
    "plan_review.json",
    "validation_plan_proposal.json",
    "validation_plan_review.json",
    "implementation_report.json",
    "change_manifest.json",
    "repair_report.json",
    "review_report.json",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path)
    args = parser.parse_args()

    workspace_output = args.run / "workspace" / "prototype" / "output"
    reports_dir = args.run / "agent_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    reports: list[dict] = []
    for name in REPORT_NAMES:
        src = workspace_output / name
        if src.exists():
            dst = reports_dir / name
            shutil.copy2(src, dst)
            reports.append({"name": name, "path": str(dst.relative_to(args.run))})

    write_json(args.run / "output" / "agent_reports.json", {"reports": reports})
    print(f"Collected agent reports: {len(reports)}")


if __name__ == "__main__":
    main()
