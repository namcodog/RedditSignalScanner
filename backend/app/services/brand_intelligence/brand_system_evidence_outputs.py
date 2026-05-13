from __future__ import annotations

from collections.abc import Mapping


def render_brand_system_evidence_markdown(payload: Mapping[str, object]) -> str:
    summary = _mapping(payload.get("summary"))
    lines = [
        "# Brand System Evidence Pack",
        "",
        f"- source: `{payload.get('source', '')}`",
        f"- db_writes: `{_bool_text(payload.get('db_writes'))}`",
        f"- frontend_display: `{_bool_text(payload.get('frontend_display'))}`",
        f"- miniapp_snapshot_fields: `{_bool_text(payload.get('miniapp_snapshot_fields'))}`",
        f"- profile: `{payload.get('profile', '')}`",
        f"- brands: `{summary.get('brand_count', 0)}`",
        f"- mentions: `{summary.get('mention_count', 0)}`",
        "",
        "## System Use",
        "",
        "- 主系统：给社区推荐和卡片解释提供品牌证据。",
        "- Hotpost：给日常 sidecar 和语义审核队列提供品牌上下文。",
        "- 小程序：通过更准的卡片和推荐理由间接受益，不直接维护品牌池。",
        "",
        "## Interest Tag Evidence",
        "",
        "| Tag | Brands | Mentions | Top Brands |",
        "|---|---:|---:|---|",
    ]
    for row in _list_of_mappings(payload.get("interest_tag_evidence")):
        lines.append(
            f"| {_cell(_text(row.get('interest_tag')))} | {_int(row.get('brand_count'))} | "
            f"{_int(row.get('mention_count'))} | {_cell(_text(row.get('top_brands')))} |"
        )
    lines.extend(
        [
            "",
            "## Community Brand Evidence",
            "",
            "| Community | Brands | Top Brands |",
            "|---|---:|---|",
        ]
    )
    for row in _list_of_mappings(payload.get("community_brand_evidence"))[:30]:
        lines.append(
            f"| {_cell(_text(row.get('community')))} | {_int(row.get('brand_count'))} | "
            f"{_cell(_text(row.get('top_brands')))} |"
        )
    return "\n".join(lines).rstrip() + "\n"


def _mapping(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _list_of_mappings(value: object) -> list[Mapping[str, object]]:
    return (
        [item for item in value if isinstance(item, dict)]
        if isinstance(value, list)
        else []
    )


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _int(value: object) -> int:
    return int(value) if isinstance(value, int | str) and str(value).isdigit() else 0


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _cell(value: str) -> str:
    return value.replace("|", "\\|")
