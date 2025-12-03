"""
Skill run history helpers.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
HISTORY_FILE = PROJECT_ROOT / "skills" / "run_history.jsonl"


def append_history(entry: Dict[str, Any]) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry["timestamp"] = datetime.utcnow().isoformat()
    with HISTORY_FILE.open("a") as f:
        f.write(json.dumps(entry) + "\n")

