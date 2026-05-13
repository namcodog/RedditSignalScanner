from __future__ import annotations

from typing import Mapping, cast


def render_brand_ops_sidecar_markdown(payload: Mapping[str, object]) -> str:
    summary = _mapping(payload.get("summary"))
    db_status = _mapping(payload.get("db_write_status"))
    evidence = _mapping(payload.get("system_evidence_summary"))
    lines = [
        "# Brand Intelligence Daily Sidecar",
        "",
        f"- date: `{_text(payload.get('report_date'))}`",
        f"- blocks_publish: `{_bool_text(payload.get('blocks_publish'))}`",
        f"- auto_write_semantic_lexicon: `{_bool_text(payload.get('auto_write_semantic_lexicon'))}`",
        f"- cards_scanned: `{_int(summary.get('cards_scanned'))}`",
        f"- brands_observed: `{_int(summary.get('brands_observed'))}`",
        f"- verified_brands: `{_int(summary.get('verified_brands'))}`",
        f"- new_brand_candidates: `{_int(summary.get('new_brand_candidates'))}`",
        f"- noise_items: `{_int(summary.get('noise_items'))}`",
        f"- system_evidence_brands: `{_int(evidence.get('brand_count'))}`",
        f"- db_writes: `{_bool_text(db_status.get('db_writes'))}`",
        "",
        "## Daily Operator Checklist",
        "",
        "- 记录新增品牌候选和最高证据。",
        "- 记录 verified 品牌和对应兴趣标签。",
        "- 记录系统证据包是否可用，不阻塞出卡。",
        "- 记录 rejected/noise 样本，不进入品牌池。",
        "- 记录 DB 写入状态；默认只读或 dry-run。",
        "",
        "## New Brand Candidates",
        "",
        *_brand_table(payload.get("new_brand_candidates")),
        "",
        "## Verified Brands",
        "",
        *_brand_table(payload.get("verified_brands")),
        "",
        "## Noise Items",
        "",
        *_brand_table(payload.get("noise_items")),
        "",
        "## Semantic Review Queue",
        "",
        *_queue_table(payload.get("semantic_review_queue")),
    ]
    return "\n".join(lines).rstrip() + "\n"


def _brand_table(value: object) -> list[str]:
    rows = _rows(value)
    if not rows:
        return ["- none"]
    lines = [
        "| Brand | Status | Mentions | Communities | Tags |",
        "|---|---:|---:|---:|---|",
    ]
    lines.extend(
        f"| {_cell(_text(row.get('canonical_name')))} | {_cell(_text(row.get('review_status')))} | {_int(row.get('mention_count'))} | {_int(row.get('community_count'))} | {_cell(', '.join(_strings(row.get('interest_tags'))))} |"
        for row in rows
    )
    return lines


def _queue_table(value: object) -> list[str]:
    rows = _rows(value)
    if not rows:
        return ["- none"]
    lines = ["| Brand | Action | Auto Apply | Tags |", "|---|---|---:|---|"]
    lines.extend(
        f"| {_cell(_text(row.get('canonical_name')))} | {_cell(_text(row.get('review_action')))} | `{_bool_text(row.get('auto_apply'))}` | {_cell(', '.join(_strings(row.get('interest_tags'))))} |"
        for row in rows
    )
    return lines


def _rows(value: object) -> list[dict[str, object]]:
    return (
        [_mapping(item) for item in value if isinstance(item, dict)]
        if isinstance(value, list)
        else []
    )


def _mapping(value: object) -> dict[str, object]:
    return dict(cast(Mapping[str, object], value)) if isinstance(value, dict) else {}


def _strings(value: object) -> list[str]:
    return (
        [item for item in value if isinstance(item, str)]
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
