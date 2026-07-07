from __future__ import annotations

import sys
from pathlib import Path

# Keep the historical `python3 tools/run_pipeline.py ...` command working while
# the implementation lives under prototype_pipeline/.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from prototype_pipeline.cli.run_pipeline import main


if __name__ == "__main__":
    main()
