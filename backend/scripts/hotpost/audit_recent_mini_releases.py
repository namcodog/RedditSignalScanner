from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.hotpost.mini_release_trend_audit import (
    DEFAULT_BASELINE_RELEASE_ID,
    DEFAULT_REQUIRED_NEW_RELEASES,
    audit_recent_release_payloads,
    load_release_payloads,
)


ROOT = BACKEND_ROOT.parent
DEFAULT_RELEASES_DIR = BACKEND_ROOT / "data" / "hotpost" / "mini_snapshots" / "releases"
DEFAULT_OUTPUT = ROOT / "reports" / "evals" / "mini-release-trend-audit-latest.json"


def run_release_trend_audit(
    *,
    releases_dir: Path = DEFAULT_RELEASES_DIR,
    display_limit: int = DEFAULT_REQUIRED_NEW_RELEASES,
    output: Path = DEFAULT_OUTPUT,
    baseline_release_id: str = DEFAULT_BASELINE_RELEASE_ID,
) -> dict:
    payloads = load_release_payloads(releases_dir)
    summary = audit_recent_release_payloads(
        payloads,
        display_limit=max(display_limit, 1),
        baseline_release_id=baseline_release_id,
        required_new_releases=DEFAULT_REQUIRED_NEW_RELEASES,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit recent mini releases for rolling inventory stability.")
    parser.add_argument("--limit", type=int, default=DEFAULT_REQUIRED_NEW_RELEASES, help="How many recent release summaries to print.")
    parser.add_argument("--releases-dir", type=Path, default=DEFAULT_RELEASES_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="JSON output path.")
    parser.add_argument("--baseline-release-id", default=DEFAULT_BASELINE_RELEASE_ID)
    args = parser.parse_args()

    summary = run_release_trend_audit(
        releases_dir=args.releases_dir,
        display_limit=max(args.limit, 1),
        output=args.output,
        baseline_release_id=str(args.baseline_release_id or DEFAULT_BASELINE_RELEASE_ID),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
