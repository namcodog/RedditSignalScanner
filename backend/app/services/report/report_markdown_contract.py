from __future__ import annotations

import re
from typing import Optional, Any

_SECTION_PATTERN = re.compile(
    r"##\s+(\d+)\.\s+([^\n]+)\n([\s\S]*?)(?=\n##\s+\d+\.\s+|$)"
)

_FIXED_SECTION_TITLES = (
    (1, "开篇概览"),
    (2, "决策风向标"),
    (3, "概览（市场健康度诊断）"),
    (4, "核心战场推荐（画像分级）"),
    (5, "用户痛点拆解"),
    (6, "关键决策驱动力"),
    (7, "商业机会"),
)


def _parse_sections(markdown: str) -> dict[int, str]:
    sections: dict[int, str] = {}
    for match in _SECTION_PATTERN.finditer(markdown or ""):
        order = int(match.group(1))
        title = str(match.group(2) or "").strip()
        body = str(match.group(3) or "").strip()
        sections[order] = f"{title}\n{body}".strip()
    return sections


def validate_narrative_markdown_against_canonical(
    *,
    markdown: str,
    report_structured:Optional[ dict[str, Any]],
) -> list[str]:
    if not report_structured:
        return ["missing canonical report"]

    issues: list[str] = []
    sections = _parse_sections(markdown)

    if len(sections) != len(_FIXED_SECTION_TITLES):
        issues.append(
            f"markdown section count mismatch: expected {len(_FIXED_SECTION_TITLES)}, got {len(sections)}"
        )

    for order, expected_title in _FIXED_SECTION_TITLES:
        text = sections.get(order, "")
        if not text:
            issues.append(f"missing markdown section {order}")
            continue
        actual_title = text.splitlines()[0].strip()
        if actual_title != expected_title:
            issues.append(
                f'section {order} title mismatch: expected "{expected_title}", got "{actual_title}"'
            )

    section4 = sections.get(4, "")
    for battlefield in report_structured.get("battlefields") or []:
        name = str(battlefield.get("name") or "").strip()
        if name and name not in section4:
            issues.append(f"battlefield missing from markdown section 4: {name}")

    section5 = sections.get(5, "")
    for pain_point in report_structured.get("pain_points") or []:
        title = str(pain_point.get("title") or "").strip()
        if title and title not in section5:
            issues.append(f"pain point missing from markdown section 5: {title}")

    section6 = sections.get(6, "")
    for driver in report_structured.get("drivers") or []:
        title = str(driver.get("title") or "").strip()
        if title and title not in section6:
            issues.append(f"driver missing from markdown section 6: {title}")

    section7 = sections.get(7, "")
    for opportunity in report_structured.get("opportunities") or []:
        title = str(opportunity.get("title") or "").strip()
        if title and title not in section7:
            issues.append(f"opportunity missing from markdown section 7: {title}")

    return issues


__all__ = ["validate_narrative_markdown_against_canonical"]
