#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _pct(x: float | int | None) -> str:
    try:
        return f"{float(x) * 100:.0f}%"
    except Exception:
        return "-"


def _bool_cn(v: bool | None) -> str:
    return "是" if v else "否"


SENTIMENT_ZH = {"positive": "正面", "negative": "负面", "mixed": "中性"}


def _cn(text: str) -> str:
    """Very simple phrase-level CN translation (best-effort)."""
    if not text:
        return ""
    repl = {
        "Users": "用户",
        "teams": "团队",
        "leaders": "管理层",
        "leadership": "管理层",
        "automation": "自动化",
        "workflow": "流程",
        "export": "导出",
        "report": "报告",
        "research": "研究",
        "ops": "运营",
        "slow": "很慢",
        "confusing": "令人困惑",
        "broken": "有问题",
        "frustrating": "令人沮丧",
        "looking for": "正在寻找",
        "need": "需要",
        "wish": "希望",
        "better": "更好的",
        "alternative": "替代方案",
        "summary": "摘要",
        "insights": "洞察",
        "discussion": "讨论",
        "entrepreneurs": "创业者",
        "entrepreneur": "创业者",
        "startup": "初创",
        "startups": "初创公司",
        "founder": "创始人",
        "product": "产品",
        "user": "用户",
        "feedback": "反馈",
        "growth": "增长",
        "marketing": "营销",
        "sales": "销售",
        "pricing": "定价",
        "research": "调研",
        "ai": "AI",
        "model": "模型",
        "automation": "自动化",
        "export": "导出",
        "reporting": "报表",
        "note": "笔记",
        "discussion": "讨论",
        "summary": "摘要",
    }
    out = text
    for k, v in repl.items():
        out = out.replace(k, v).replace(k.capitalize(), v)
    return out


def _top_communities(communities: List[Dict[str, Any]], k: int = 5) -> List[Tuple[str, int]]:
    arr = [(str(c.get("name", "-")), int(c.get("mentions", 0) or 0)) for c in communities]
    arr.sort(key=lambda x: x[1], reverse=True)
    return arr[:k]


def render_markdown(obj: Dict[str, Any]) -> str:
    desc = obj.get("description", "")
    src = obj.get("sources", {})
    ins = obj.get("insights", {})
    communities: List[Dict[str, Any]] = src.get("communities_detail") or []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines: List[str] = []
    lines.append(f"# 市场洞察报告（中文增强版）\n")
    lines.append(f"- 任务描述：{desc}")
    lines.append(f"- 生成时间：{ts}")
    lines.append(f"- 已分析帖子：{src.get('posts_analyzed', 0)}")
    lines.append(f"- 缓存命中率：{_pct(src.get('cache_hit_rate', 0))}")
    lines.append(f"- Reddit API 调用：{src.get('reddit_api_calls', 0)}\n")

    # 中文摘要（一屏看懂）
    lines.append("## 结论摘要（中文）\n")
    topc = _top_communities(communities, 5)
    if topc:
        comm_txt = "、".join([f"{name}（{cnt}次）" for name, cnt in topc])
        lines.append(f"- 相关社区集中在：{comm_txt}")
    pain = ins.get("pain_points") or []
    if pain:
        pains = [(_cn(str(p.get('description','')))) or str(p.get('description','')) for p in pain][:3]
        lines.append("- 用户主要痛点：" + "；".join(pains))
    opp = ins.get("opportunities") or []
    if opp:
        opps = [(_cn(str(o.get('description','')))) or str(o.get('description','')) for o in opp][:3]
        lines.append("- 机会方向（Top3）：" + "；".join(opps))
    lines.append("")

    # Top communities
    if communities:
        lines.append("## 相关社区（Top）\n")
        lines.append("| 社区 | 次提及 | 每日帖子 | 平均评论长度 | 缓存命中 | 来自缓存 |")
        lines.append("|---|---:|---:|---:|---:|:---:|")
        for c in communities[:10]:
            lines.append(
                f"| {c.get('name','-')} | {c.get('mentions',0)} | {c.get('daily_posts','-')} | "
                f"{c.get('avg_comment_length','-')} | {_pct(c.get('cache_hit_rate',0))} | "
                f"{_bool_cn(c.get('from_cache', False))} |"
            )
        lines.append("")

    # Pain points
    pain = ins.get("pain_points") or []
    if pain:
        lines.append("## 用户痛点（中文+原文）\n")
        for i, p in enumerate(pain, 1):
            en = str(p.get("description", ""))
            zh = _cn(en)
            lines.append(f"{i}. {zh if zh else en}")
            if zh and zh != en:
                lines.append(f"   - 原文：{en}")
            if p.get("frequency") is not None:
                lines.append(f"   - 频次：{p.get('frequency')}")
            if p.get("severity"):
                lines.append(f"   - 严重程度：{p.get('severity')}")
        lines.append("")

    # Competitors
    comp = ins.get("competitors") or []
    if comp:
        lines.append("## 竞品概览（中文）\n")
        lines.append("| 竞品 | 提及 | 情感 | 份额(估) | 优势 | 劣势 |")
        lines.append("|---|---:|:---:|---:|---|---|")
        for c in comp:
            strengths = "; ".join(map(str, c.get("strengths") or []))
            weaknesses = "; ".join(map(str, c.get("weaknesses") or []))
            lines.append(
                f"| {c.get('name','-')} | {c.get('mentions',0)} | {SENTIMENT_ZH.get(c.get('sentiment','mixed'),'中性')} | "
                f"{c.get('market_share',0)}% | {strengths} | {weaknesses} |"
            )
        lines.append("")

    # Opportunities
    opp = ins.get("opportunities") or []
    if opp:
        lines.append("## 商业机会（中文+原文）\n")
        for i, o in enumerate(opp, 1):
            en = str(o.get("description", ""))
            zh = _cn(en)
            lines.append(f"{i}. {zh if zh else en}")
            if zh and zh != en:
                lines.append(f"   - 原文：{en}")
            lines.append(f"   - 相关度：{_pct(o.get('relevance_score',0))}")
            if o.get("potential_users"):
                lines.append(f"   - 潜在用户：{o['potential_users']}")
            if o.get("key_insights"):
                keys = ", ".join(map(str, o.get("key_insights") or []))
                lines.append(f"   - 关键词：{keys}")
        lines.append("")

    # 行动建议（根据机会与痛点拉取三条）
    suggestions: List[str] = []
    if opp:
        for o in opp[:3]:
            desc = _cn(str(o.get("description",""))) or str(o.get("description",""))
            suggestions.append(f"围绕“{desc}”设计最小可行方案，验证 2 周内能否获得首批试用用户。")
    if pain:
        for p in pain[:2]:
            d = _cn(str(p.get("description",""))) or str(p.get("description",""))
            suggestions.append(f"优先修复/覆盖用户痛点：“{d}”，并在相关社区发起可验证的反馈贴。")
    if suggestions:
        lines.append("## 行动建议\n")
        for i, s in enumerate(suggestions, 1):
            lines.append(f"{i}. {s}")
        lines.append("")

    lines.append(
        "> 注：以上中文为自动粗译，便于阅读；报告基于 Reddit 公开数据与缓存优先策略，建议结合原帖核对关键信息。\n"
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render analysis JSON to Markdown")
    parser.add_argument("input", help="Path to analysis JSON file")
    parser.add_argument("--out", help="Output Markdown file path", default=None)
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text())
    md = render_markdown(data)
    out = Path(args.out) if args.out else Path(args.input).with_suffix(".md")
    out.write_text(md)
    print(str(out))


if __name__ == "__main__":
    main()
