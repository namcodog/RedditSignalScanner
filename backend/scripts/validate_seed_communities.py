from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


NAME_RE = re.compile(r"^r/[A-Za-z0-9_][A-Za-z0-9_]*$")


@dataclass
class ValidationResult:
    total: int
    valid: int
    invalid: int
    duplicates: List[str]
    invalid_names: List[str]


def validate_seed_file(path: Path) -> ValidationResult:
    raw = json.loads(path.read_text(encoding="utf-8"))
    items: List[Dict[str, Any]] = list(raw.get("seed_communities") or [])
    seen: set[str] = set()
    dupes: List[str] = []
    invalid_names: List[str] = []
    valid = 0

    for item in items:
        name = str(item.get("name", "")).strip()
        if not NAME_RE.match(name):
            invalid_names.append(name)
            continue
        if name in seen:
            dupes.append(name)
            continue
        seen.add(name)
        valid += 1

    return ValidationResult(
        total=len(items),
        valid=valid,
        invalid=len(items) - valid - len(dupes),
        duplicates=dupes,
        invalid_names=invalid_names,
    )


def main() -> None:
    seed_path = Path("backend/config/seed_communities.json")
    report_path = Path("backend/config/seed_communities_validation_report.json")
    if not seed_path.exists():
        print("Seed file not found:", seed_path)
        return
    result = validate_seed_file(seed_path)
    report = {
        "total": result.total,
        "valid": result.valid,
        "invalid": result.invalid,
        "duplicates": result.duplicates,
        "invalid_names": result.invalid_names,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Validation report written to:", report_path)


if __name__ == "__main__":
    main()

