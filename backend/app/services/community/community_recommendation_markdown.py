from __future__ import annotations

from app.services.community.community_recommendation_models import RecommendationPreview


def render_markdown(preview: RecommendationPreview) -> str:
    lines = [
        "# Community Recommendation Preview",
        "",
        "- DB writes: `false`",
        "- user_input_required: `false`",
        "- source: `existing data + semantic evidence + activity signals`",
        "",
        "## Acceptance",
        "",
        f"- passed: `{str(preview.acceptance.passed).lower()}`",
        f"- ready_count: `{preview.acceptance.ready_count}`",
        f"- historical_count: `{preview.acceptance.historical_count}`",
        f"- watching_count: `{preview.acceptance.watching_count}`",
        f"- generic_count: `{preview.acceptance.generic_count}`",
        f"- longtail_count: `{preview.acceptance.longtail_count}`",
        "- blockers: `"
        + (", ".join(preview.acceptance.blockers) if preview.acceptance.blockers else "none")
        + "`",
        "",
        "## Interest Tags",
        "",
        "| Tag | Group | Status | Available Communities | Description |",
        "|---|---|---|---:|---|",
    ]
    for tag in preview.tags:
        lines.append(
            f"| {tag.name} | {tag.group} | {tag.status} | "
            f"{tag.ready_community_count} | {tag.description} |"
        )
    for tag in preview.tags:
        lines.extend(["", f"## {tag.name}", "", f"- status: `{tag.status}`", ""])
        lines.append("| Community | Activity | Best For | Evidence | Score | Reason |")
        lines.append("|---|---|---|---|---:|---|")
        for item in preview.recommendations.get(tag.tag_id, ()):
            lines.append(
                "| "
                + item.community
                + " | "
                + item.activity_label
                + " | "
                + item.best_for
                + " | "
                + (item.evidence_teaser or "-")
                + " | "
                + f"{item.score:.2f}"
                + " | "
                + " / ".join(item.reasons)
                + " |"
            )
    lines.extend(["", "## Debug Evidence", ""])
    for tag in preview.tags:
        lines.extend(["", f"### {tag.name}", ""])
        lines.append(f"- source_refs: `{', '.join(tag.source_refs)}`")
        lines.append(f"- evidence_sources: `{', '.join(tag.evidence_sources)}`")
        lines.append("")
        lines.append("| Community | Status | Role | Latest | Terms | Evidence | Risk | Debug Summary |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for item in preview.recommendations.get(tag.tag_id, ()):
            lines.append(
                "| "
                + item.community
                + " | "
                + item.status
                + " | "
                + item.role
                + " | "
                + (item.latest_activity_at or "-")
                + " | "
                + (", ".join(item.semantic_terms) if item.semantic_terms else "-")
                + " | "
                + ", ".join(item.evidence_sources)
                + " | "
                + (", ".join(item.risk_flags) if item.risk_flags else "none")
                + " | "
                + " / ".join(item.evidence_summary)
                + " |"
            )
    return "\n".join(lines).rstrip() + "\n"


__all__ = ["render_markdown"]
