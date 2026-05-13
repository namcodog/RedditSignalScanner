from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.scripts_support.env_loader import load_backend_env
from app.services.hotpost.card_payload_store import load_published_cards


DEFAULT_OUTPUT_DIR = ROOT.parents[0] / "reports" / "ops-log"
DEFAULT_TIMEZONE = "Asia/Shanghai"
DEFAULT_RECENT_DAYS = 5
LANE_ORDER = ("hot", "signal", "breakdown")
SCOPE_ORDER = ("商业增长与运营", "AI 与自动化", "电商与卖家")


@dataclass(frozen=True)
class PublishDay:
    day: str
    timezone: str
    cards: list[dict]
    lane_counts: Counter[str]
    scope_counts: Counter[str]
    scope_names: dict[str, str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="导出最近几天的发卡运营日志。")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--days", type=int, default=DEFAULT_RECENT_DAYS)
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    return parser.parse_args()


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _markdown_cell(value: object | None) -> str:
    if value in (None, ""):
        return "-"
    text = str(value).replace("\n", " ").strip()
    return text.replace("|", "\\|")


def _format_local_hm(value: str, timezone: str) -> str:
    zone = ZoneInfo(timezone)
    return _parse_iso(value).astimezone(zone).strftime("%H:%M")


def _pick_top_community(card: dict) -> str | None:
    top_community = card.get("top_community")
    if isinstance(top_community, str) and top_community.strip():
        return top_community.strip()
    source_module = card.get("source_module") or {}
    nested = source_module.get("top_community")
    if isinstance(nested, str) and nested.strip():
        return nested.strip()
    primary = source_module.get("primary_communities") or []
    if isinstance(primary, list):
        for item in primary:
            if isinstance(item, str) and item.strip():
                return item.strip()
    return None


def _render_counter(counter: Counter[str], order: tuple[str, ...], labels: dict[str, str]) -> str:
    parts: list[str] = []
    for key in order:
        if counter.get(key):
            parts.append(f"{labels.get(key, key)} {counter[key]}")
    extras = sorted(key for key in counter if key not in order and counter[key])
    for key in extras:
        parts.append(f"{labels.get(key, key)} {counter[key]}")
    return " / ".join(parts) if parts else "-"


def build_recent_publish_days(cards: list[dict], *, days: int, timezone: str) -> list[PublishDay]:
    zone = ZoneInfo(timezone)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for card in cards:
        published_at = card.get("published_at")
        if not published_at:
            continue
        local_day = _parse_iso(published_at).astimezone(zone).date().isoformat()
        grouped[local_day].append(card)

    selected_days = sorted(grouped.keys(), reverse=True)[: max(days, 0)]
    result: list[PublishDay] = []
    for day in selected_days:
        day_cards = sorted(grouped[day], key=lambda item: item["published_at"], reverse=True)
        lane_counts = Counter(str(item.get("lane") or "unknown") for item in day_cards)
        scope_counts = Counter(_scope_display_name(item) for item in day_cards)
        scope_names = {
            _scope_display_name(item): _scope_display_name(item)
            for item in day_cards
        }
        result.append(
            PublishDay(
                day=day,
                timezone=timezone,
                cards=day_cards,
                lane_counts=lane_counts,
                scope_counts=scope_counts,
                scope_names=scope_names,
            )
        )
    return result


def _scope_display_name(card: dict) -> str:
    return str(
        card.get("source_domain_name")
        or card.get("source_scope_name")
        or card.get("source_scope_id")
        or "未知类别"
    )


def render_day_markdown(publish_day: PublishDay) -> str:
    lane_labels = {"hot": "hot", "signal": "signal", "breakdown": "breakdown"}
    scope_labels = {key: publish_day.scope_names.get(key, key) for key in publish_day.scope_counts}
    lines = [
        f"# {publish_day.day} 运营日志",
        "",
        f"- 统计口径：按正式发布卡的 `published_at`（`{publish_day.timezone}`）归档",
        f"- 总发卡：`{len(publish_day.cards)}`",
        f"- 结构分布：`{_render_counter(publish_day.lane_counts, LANE_ORDER, lane_labels)}`",
        f"- 类别分布：`{_render_counter(publish_day.scope_counts, SCOPE_ORDER, scope_labels)}`",
        "",
        "## 卡片清单",
        "",
        "| 时间 | card_id | 标题 | 结构 | 类别 | 专题包 | 主社区 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for card in publish_day.cards:
        lines.append(
            "| "
            + " | ".join(
                [
                    _markdown_cell(_format_local_hm(card["published_at"], publish_day.timezone)),
                    _markdown_cell(card.get("card_id")),
                    _markdown_cell(card.get("title")),
                    _markdown_cell(f"{card.get('lane', '-')} / {card.get('card_type', '-')}"),
                    _markdown_cell(card.get("source_scope_name") or card.get("source_scope_id")),
                    _markdown_cell(card.get("topic_pack_id")),
                    _markdown_cell(_pick_top_community(card)),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def render_index_markdown(publish_days: list[PublishDay], *, timezone: str) -> str:
    lines = [
        "# 运营日志",
        "",
        f"- 统计口径：当前 `latest release` 的正式发布卡，按 `published_at`（`{timezone}`）分日归档",
        "- 作用：快速回看每天发了哪些卡、结构怎么配、类别怎么分布",
        f"- 当前展示：最近 `{len(publish_days)}` 个有发布动作的日期",
        "",
        "## 日期索引",
        "",
        "| 日期 | 发卡总数 | 结构分布 | 类别分布 | 明细 |",
        "| --- | --- | --- | --- | --- |",
    ]
    lane_labels = {"hot": "hot", "signal": "signal", "breakdown": "breakdown"}
    for publish_day in publish_days:
        scope_labels = {key: publish_day.scope_names.get(key, key) for key in publish_day.scope_counts}
        lines.append(
            "| "
            + " | ".join(
                [
                    publish_day.day,
                    str(len(publish_day.cards)),
                    _markdown_cell(_render_counter(publish_day.lane_counts, LANE_ORDER, lane_labels)),
                    _markdown_cell(_render_counter(publish_day.scope_counts, SCOPE_ORDER, scope_labels)),
                    f"[查看]({publish_day.day}.md)",
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def export_ops_log(*, output_dir: Path, days: int, timezone: str) -> dict[str, object]:
    cards = load_published_cards()
    publish_days = build_recent_publish_days(cards, days=days, timezone=timezone)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "INDEX.md").write_text(
        render_index_markdown(publish_days, timezone=timezone),
        encoding="utf-8",
    )
    for publish_day in publish_days:
        (output_dir / f"{publish_day.day}.md").write_text(
            render_day_markdown(publish_day),
            encoding="utf-8",
        )
    return {
        "output_dir": str(output_dir),
        "days_exported": len(publish_days),
        "daily_counts": {publish_day.day: len(publish_day.cards) for publish_day in publish_days},
    }


def main() -> None:
    load_backend_env()
    args = parse_args()
    result = export_ops_log(output_dir=args.output_dir, days=args.days, timezone=args.timezone)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
