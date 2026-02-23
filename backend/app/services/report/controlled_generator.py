#!/usr/bin/env python3
from __future__ import annotations

"""Controlled markdown report generator for Spec 011 Stage 3."""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


# ---------------------------------------------------------------------------
# Data helpers


@dataclass
class EvidenceRecord:
    evid: str
    layer: str
    source: str
    snippet: str


class SafeDict(dict):
    def __missing__(self, key: str) -> str:  # pragma: no cover - simple fallback
        return "N/A"


def _read_json(path: Path | None) -> dict:
    if not path:
        return {}
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _pct(value: float | int | None) -> str:
    if value is None:
        return "0"
    if value <= 1:
        return f"{value * 100:.1f}"
    return f"{value:.1f}"


def _top_terms_from_lexicon(
    lexicon: dict,
    *,
    layer: str,
    category: str,
    limit: int,
) -> List[str]:
    layers = lexicon.get("layers", {})
    cat_entries = layers.get(layer, {}).get(category, []) if isinstance(layers, dict) else []
    terms = sorted(cat_entries, key=lambda item: float(item.get("weight", 0.0)), reverse=True)
    names: List[str] = []
    for item in terms:
        name = str(item.get("canonical", "")).strip()
        if name:
            names.append(name)
        if len(names) >= limit:
            break
    return names


def _layer_coverage(metrics: dict, layer: str) -> str:
    for entry in metrics.get("layer_coverage", []) or []:
        if str(entry.get("layer")) == layer:
            return _pct(float(entry.get("coverage", 0.0)))
    return _pct(None)


def _layer_coverage_float(metrics: dict, layer: str) -> float:
    for entry in metrics.get("layer_coverage", []) or []:
        if str(entry.get("layer")) == layer:
            try:
                return float(entry.get("coverage", 0.0) or 0.0)
            except Exception:
                return 0.0
    return 0.0


def _clean_snippet(text: str | None) -> str:
    if not text:
        return ""
    snippet = " ".join(text.strip().split())
    return snippet.replace("|", "/")[:180]


def _register_evidence(
    records: List[EvidenceRecord],
    *,
    layer: str,
    source: str,
    snippet: str,
) -> str | None:
    clean = _clean_snippet(snippet)
    if not clean:
        return None
    evid = f"EV-{layer}-{len(records) + 1:03d}"
    records.append(EvidenceRecord(evid, layer, source, clean))
    return evid


def _list_to_string(items: Sequence[str], *, sep: str = " / ") -> str:
    filtered = [item for item in items if item]
    return sep.join(filtered) if filtered else "待补充"


def _collect_pain_points(insights: dict) -> List[dict]:
    pains = insights.get("pain_points") or []
    pains_sorted = sorted(pains, key=lambda item: int(item.get("frequency", 0)), reverse=True)
    return pains_sorted


def _competitor_layers(insights: dict, code: str) -> List[dict]:
    layers = insights.get("competitor_layers_summary") or []
    return [entry for entry in layers if str(entry.get("layer", "")).upper().startswith(code.upper())]


def _channel_breakdown(insights: dict) -> List[str]:
    channels = insights.get("channel_breakdown") or []
    return [str(item.get("name", "")).strip() for item in channels if item.get("name")]


def _action_items(insights: dict) -> List[dict]:
    return insights.get("action_items") or insights.get("opportunities") or []


def build_context(
    analysis: dict,
    lexicon: dict | None,
    metrics: dict | None,
    *,
    task_id: str,
) -> tuple[Dict[str, str], List[EvidenceRecord]]:
    lexicon_data = lexicon or {}
    metrics_data = metrics or {}
    insights = analysis.get("insights") or {}
    sources = analysis.get("sources") or {}

    context: Dict[str, str] = {
        "task_id": task_id,
        "overall_coverage": _pct(metrics_data.get("entity_coverage", {}).get("overall")),
        "pain_coverage": _pct(metrics_data.get("entity_coverage", {}).get("pain_points")),
        "brand_coverage": _pct(metrics_data.get("entity_coverage", {}).get("brands")),
        "top10_share": _pct(metrics_data.get("entity_coverage", {}).get("top10_unique_share")),
    }

    evidence_records: List[EvidenceRecord] = []

    # L1 summary
    l1_terms = _top_terms_from_lexicon(lexicon_data, layer="L1", category="features", limit=5)
    context["L1_terms"] = _list_to_string(l1_terms)
    context["L1_coverage"] = _layer_coverage(metrics_data, "L1")

    clusters = insights.get("pain_clusters") or []
    l1_evidence_ids: List[str] = []
    for cluster in clusters:
        for sample in cluster.get("samples", [])[:2]:
            evid = _register_evidence(
                evidence_records,
                layer="L1",
                source=cluster.get("topic", "cluster"),
                snippet=sample,
            )
            if evid:
                l1_evidence_ids.append(evid)
        if len(l1_evidence_ids) >= 2:
            break
    context["L1_evidence_ids"] = _list_to_string(l1_evidence_ids, sep=", ")

    # L2 summary
    l2_layers = _competitor_layers(insights, "L2")
    platforms: List[str] = []
    for entry in l2_layers:
        for comp in entry.get("top_competitors", [])[:3]:
            name = str(comp.get("name", "")).strip()
            if name:
                platforms.append(name)
    context["L2_platforms"] = _list_to_string(platforms)
    l2_pain = _top_terms_from_lexicon(lexicon_data, layer="L2", category="pain_points", limit=4)
    context["L2_pain_points"] = _list_to_string(l2_pain)
    communities = sources.get("communities") or []
    context["L2_communities_count"] = str(len(communities))
    l2_evidence_ids: List[str] = []
    for entry in l2_layers:
        snippet = entry.get("threats") or ", ".join(platforms[:2])
        evid = _register_evidence(
            evidence_records,
            layer="L2",
            source=entry.get("label", "L2"),
            snippet=snippet,
        )
        if evid:
            l2_evidence_ids.append(evid)
        if len(l2_evidence_ids) >= 2:
            break
    context["L2_evidence_ids"] = _list_to_string(l2_evidence_ids, sep=", ")

    # L3 summary
    context["L3_tools"] = _list_to_string(_channel_breakdown(insights)[:3])
    context["L3_methods"] = _list_to_string(_top_terms_from_lexicon(lexicon_data, layer="L3", category="features", limit=4))
    context["L3_coverage"] = _layer_coverage(metrics_data, "L3")
    l3_evidence_ids: List[str] = []
    for entry in _competitor_layers(insights, "L3"):
        evid = _register_evidence(
            evidence_records,
            layer="L3",
            source=entry.get("label", "L3"),
            snippet=entry.get("threats") or _list_to_string([c.get("name") for c in entry.get("top_competitors", [])]),
        )
        if evid:
            l3_evidence_ids.append(evid)
        if len(l3_evidence_ids) >= 2:
            break
    context["L3_evidence_ids"] = _list_to_string(l3_evidence_ids, sep=", ")

    # L4 summary
    pains = _collect_pain_points(insights)
    for idx in range(1, 4):
        if idx <= len(pains):
            pain = pains[idx - 1]
            context[f"L4_pain_{idx}"] = pain.get("description", f"Pain {idx}")
            context[f"L4_pain_{idx}_count"] = str(pain.get("frequency", 0))
            evidence_ids: List[str] = []
            for post in pain.get("example_posts", [])[:2]:
                source = post.get("community") or "pain"
                snippet = post.get("content") or post.get("title")
                evid = _register_evidence(
                    evidence_records,
                    layer="L4",
                    source=source,
                    snippet=snippet or pain.get("description", "pain evidence"),
                )
                if evid:
                    evidence_ids.append(evid)
            if not evidence_ids and pain.get("user_examples"):
                evid = _register_evidence(
                    evidence_records,
                    layer="L4",
                    source="user_quote",
                    snippet=pain.get("user_examples", [""])[0],
                )
                if evid:
                    evidence_ids.append(evid)
            context[f"L4_pain_{idx}_ids"] = _list_to_string(evidence_ids, sep=", ")
        else:
            context[f"L4_pain_{idx}"] = "待补充"
            context[f"L4_pain_{idx}_count"] = "0"
            context[f"L4_pain_{idx}_ids"] = "无"

    # Actions
    actions = _action_items(insights)
    for idx in range(1, 4):
        if idx <= len(actions):
            action = actions[idx - 1]
            descriptor = action.get("problem_definition") or action.get("description") or "未命名行动"
            suggestion_list = action.get("suggested_actions") or action.get("key_insights") or []
            highlight = suggestion_list[0] if suggestion_list else "待补充建议"
            context[f"action_{idx}"] = f"{descriptor} — {highlight}"
            action_evidence_ids: List[str] = []
            for evidence in action.get("evidence_chain", [])[:2]:
                snippet = evidence.get("title") or evidence.get("note")
                source = evidence.get("note") or evidence.get("url") or "action"
                evid = _register_evidence(
                    evidence_records,
                    layer=f"A{idx}",
                    source=str(source),
                    snippet=snippet,
                )
                if evid:
                    action_evidence_ids.append(evid)
            context[f"action_{idx}_ids"] = _list_to_string(action_evidence_ids, sep=", ")
        else:
            context[f"action_{idx}"] = "待补充"
            context[f"action_{idx}_ids"] = "无"

    # Fallbacks
    context.setdefault("L2_evidence_ids", "无")
    context.setdefault("L3_evidence_ids", "无")
    context.setdefault("L1_evidence_ids", "无")

    # Derived indicators for summary card (Spec010/P0 §7)
    # Allow override from analysis payload if present
    try:
        override = insights.get("ps_ratio_override")
        if isinstance(override, (int, float)) and override > 0:
            context["ps_ratio"] = f"{float(override):.1f} : 1"
        else:
            pains_count = len(insights.get("pain_points") or [])
            solutions_count = len(insights.get("opportunities") or [])
            if solutions_count > 0:
                ratio = pains_count / max(1, solutions_count)
                context["ps_ratio"] = f"{ratio:.1f} : 1"
            else:
                context["ps_ratio"] = "N/A"
    except Exception:
        context["ps_ratio"] = "N/A"

    try:
        ec = metrics_data.get("entity_coverage", {}) or {}
        brands_cov = float(ec.get("brands", 0.0) or 0.0)
        top10 = float(ec.get("top10_unique_share", 0.0) or 0.0)
        l2_cov = _layer_coverage_float(metrics_data, "L2")
        saturation = max(0.0, min(100.0, (brands_cov * 0.4 + top10 * 0.3 + l2_cov * 0.3) * 100.0))
        context["competition_saturation"] = f"{saturation:.0f}/100"
    except Exception:
        context["competition_saturation"] = "N/A"

    if evidence_records:
        table_lines = ["| ID | Layer | Source | Snippet |", "| --- | --- | --- | --- |"]
        for record in evidence_records:
            table_lines.append(
                f"| {record.evid} | {record.layer} | {record.source} | {record.snippet} |"
            )
        context["evidence_table"] = "\n".join(table_lines)
    else:
        context["evidence_table"] = "暂无证据"

    return context, evidence_records


def render_report(template_text: str, context: Dict[str, str]) -> str:
    safe_context = SafeDict({k: (v if isinstance(v, str) else str(v)) for k, v in context.items()})
    return template_text.format_map(safe_context)


def validate_report_structure(report_a: str, report_b: str) -> bool:
    def _headings(text: str) -> List[str]:
        return [line.strip() for line in text.splitlines() if line.strip().startswith("#")]

    return _headings(report_a) == _headings(report_b)


# ---------------------------------------------------------------------------
# CLI entrypoint


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Controlled report generator")
    parser.add_argument("--analysis", type=Path, help="Analysis JSON payload", required=False)
    parser.add_argument("--lexicon", type=Path, help="Semantic lexicon JSON", required=False)
    parser.add_argument("--metrics", type=Path, help="Metrics JSON", required=False)
    parser.add_argument("--template", type=Path, required=False)
    parser.add_argument("--output", type=Path, required=False)
    parser.add_argument("--task-id", default="report-task")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--report1", type=Path)
    parser.add_argument("--report2", type=Path)
    return parser


def main() -> None:  # pragma: no cover - CLI wiring
    args = _build_parser().parse_args()

    if args.validate:
        if not args.report1 or not args.report2:
            raise SystemExit("--report1 and --report2 required for --validate")
        report_a = args.report1.read_text(encoding="utf-8")
        report_b = args.report2.read_text(encoding="utf-8")
        if validate_report_structure(report_a, report_b):
            print("✅ Reports share identical structure")
            return
        raise SystemExit("❌ Report structures differ")

    if not args.analysis or not args.template or not args.output:
        raise SystemExit("--analysis, --template and --output are required for generation")

    analysis_data = _read_json(args.analysis)
    lexicon_data = _read_json(args.lexicon)
    metrics_data = _read_json(args.metrics)
    context, _ = build_context(
        analysis_data,
        lexicon_data,
        metrics_data,
        task_id=args.task_id,
    )
    template_text = args.template.read_text(encoding="utf-8")
    rendered = render_report(template_text, context)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"Report written to {args.output}")


if __name__ == "__main__":  # pragma: no cover
    main()
