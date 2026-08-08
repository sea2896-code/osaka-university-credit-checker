from __future__ import annotations

import json
from pathlib import Path


DEFAULT_RULES = Path(__file__).resolve().parents[1] / "config" / "osaka_econ_2023.yaml"


def load_rules(path: str | Path = DEFAULT_RULES) -> dict:
    """JSON-compatible YAML avoids adding a parser dependency to the MVP."""
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)
