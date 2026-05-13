from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.scripts_support.env_loader import load_backend_env
from app.services.hotpost.mini_snapshot import publish_mini_snapshot
from scripts.hotpost.audit_recent_mini_releases import DEFAULT_OUTPUT as DEFAULT_TREND_AUDIT_OUTPUT
from scripts.hotpost.audit_recent_mini_releases import run_release_trend_audit


DEFAULT_OUTPUT_DIR = ROOT / "data" / "hotpost" / "mini_snapshots"
DEFAULT_BUNDLE_DIR = ROOT.parents[0] / "hotpost-mini" / "hotpost-mini-app" / "cloudfunctions" / "miniRelease" / "data"
DEFAULT_EXTRA_BUNDLE_DIRS = [
    ROOT.parents[0] / "hotpost-mini" / "hotpost-mini-app" / "cloudfunctions" / "miniFavorites" / "data",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="导出并推送 hotpost mini snapshot。")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--bundle-dir", type=Path, default=DEFAULT_BUNDLE_DIR)
    parser.add_argument("--skip-bundle", action="store_true")
    parser.add_argument(
        "--refresh-hot-controversy",
        action="store_true",
        help="推送前在线刷新缺失的热点争议图；默认关闭，避免同步链被外部调用卡住。",
    )
    return parser.parse_args()


def main() -> None:
    load_backend_env()
    args = parse_args()
    result = publish_mini_snapshot(
        output_dir=args.output_dir,
        bundle_dir=None if args.skip_bundle else args.bundle_dir,
        bundle_dirs=[] if args.skip_bundle else DEFAULT_EXTRA_BUNDLE_DIRS,
        refresh_hot_controversy=args.refresh_hot_controversy,
    )
    trend_summary = run_release_trend_audit()
    result["trend_audit_path"] = str(DEFAULT_TREND_AUDIT_OUTPUT)
    result["trend_latest_status"] = trend_summary.get("latest_status")
    result["trend_remediation_focus"] = trend_summary.get("latest_remediation_focus")
    result["trend_remaining_new_releases"] = trend_summary.get("remaining_new_releases")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
