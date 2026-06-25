from __future__ import annotations

import json
from pathlib import Path

_SCHEMA_PATH = Path(__file__).resolve().parent / "schema" / "audfoben.json"


def load_audfoben_schema() -> dict:
    with _SCHEMA_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


AUDFOBEN_SCHEMA = load_audfoben_schema()
