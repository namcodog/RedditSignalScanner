from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.scripts_support.env_loader import load_backend_env
from app.services.hotpost.hot_lane_audit import build_hot_lane_audit


def main() -> None:
    load_backend_env()
    audit = build_hot_lane_audit()
    reports = ROOT.parent / "reports" / "evals"
    reports.mkdir(parents=True, exist_ok=True)
    json_path = reports / "hot_lane_audit_v1.json"
    md_path = reports / "hot_lane_audit_v1.md"
    json_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_to_markdown(audit), encoding="utf-8")
    print(json.dumps({"json_path": str(json_path), "md_path": str(md_path)}, ensure_ascii=False))


def _to_markdown(audit: dict) -> str:
    lines = [
        "# hot lane audit v1",
        "",
        f"- candidate_total: `{audit['candidate_total']}`",
        f"- listing_total: `{audit['listing_total']}`",
        f"- runtime_hot_total: `{audit['runtime_hot_total']}`",
        f"- runtime_hot_unpublished_total: `{audit['runtime_hot_unpublished_total']}`",
        f"- runtime_hot_published_total: `{audit['runtime_hot_published_total']}`",
        f"- runtime_hot_listing_total: `{audit['runtime_hot_listing_total']}`",
        f"- runtime_hot_search_total: `{audit['runtime_hot_search_total']}`",
        f"- runtime_signal_listing_total: `{audit['runtime_signal_listing_total']}`",
        f"- published_hot_total: `{audit['published_hot_total']}`",
        "",
        "## runtime hot by scope",
    ]
    for key, value in audit["runtime_hot_by_scope"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## runtime hot unpublished by scope"])
    for key, value in audit["runtime_hot_unpublished_by_scope"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## runtime hot unpublished candidates"])
    for item in audit["runtime_hot_candidates"]:
        lines.append(f"- `{item['candidate_id']}` | `{item['scope_id']}` | `{item['subreddit']}` | `{item['score']}/{item['num_comments']}` | {item['title']}")
    lines.extend(["", "## runtime hot already published candidates"])
    for item in audit["runtime_hot_published_candidates"]:
        lines.append(f"- `{item['candidate_id']}` | `{item['scope_id']}` | `{item['subreddit']}` | `{item['score']}/{item['num_comments']}` | {item['title']}")
    lines.extend(["", "## top listing signal candidates"])
    for item in audit["top_listing_signal_candidates"]:
        lines.append(f"- `{item['candidate_id']}` | `{item['scope_id']}` | `{item['subreddit']}` | `{item['score']}/{item['num_comments']}` | {item['title']}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
