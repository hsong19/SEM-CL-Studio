from __future__ import annotations

import re
from pathlib import Path


_PATTERNS = {
    "voltage_kv": re.compile(r"(?P<value>\d+(?:\.\d+)?)\s*kV", re.IGNORECASE),
    "beam_current_pa": re.compile(r"(?P<value>\d+(?:\.\d+)?)\s*pA", re.IGNORECASE),
    "pressure_mtorr": re.compile(r"(?P<value>\d+(?:\.\d+)?)\s*mTorr", re.IGNORECASE),
}


def parse_measurement_conditions(path: str | Path) -> dict[str, float | None]:
    name = Path(path).stem
    result: dict[str, float | None] = {}
    for key, pattern in _PATTERNS.items():
        match = pattern.search(name)
        result[key] = float(match.group("value")) if match else None
    return result

