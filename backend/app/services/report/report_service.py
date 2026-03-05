from __future__ import annotations

import asyncio
import copy
import logging
import json
import time
from dataclasses import dataclass
from typing import Any, Protocol, Mapping, Sequence
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.task import Task, TaskStatus
from app.models.user import MembershipLevel
from app.repositories.report_repository import ReportRepository
from app.services.report.t1_market_agent import ReportInputs, T1MarketReportAgent
from app.services.t1_clustering import build_pain_clusters
from app.services.t1_stats import build_stats_snapshot
from app.schemas.analysis import (
    AnalysisRead,
    CommunitySourceDetail,
    InsightsPayload,
    OpportunityReportOut,
    SourcesPayload,
    EntityLeaderboardItem,
)
from app.schemas.report_payload import (
    FallbackQuality,
    MarketHealth,
    ReportContent,
    ReportExecutiveSummary,
    ReportMetadata,
    ReportOverview,
    ReportPayload,
    ReportStats,
    SentimentBreakdown,
    TopCommunity,
)
from app.utils.url import normalize_reddit_url
from app.services.analysis import assign_competitor_layers, build_layer_summary
from app.services.report.opportunity_report import build_opportunity_reports
from app.services.llm.summarizer import LocalExtractiveSummarizer
from app.services.llm.normalizer import LocalDeterministicNormalizer
from app.services.llm.rag_conf_normalizer import (
    LocalRagConfidenceNormalizer,
    OpenAIRagConfidenceNormalizer,
)
from app.services.llm.report_prompts import (
    build_report_structured_prompt_v9,
    format_facts_for_prompt,
)
from app.services.llm.clients.openai_client import OpenAIChatClient
from pathlib import Path

try:  # Optional import for controlled summary (Spec 011)
    from app.services.report.controlled_generator import build_context as _cg_build_ctx, render_report as _cg_render
except Exception:  # pragma: no cover - keep service resilient if module unavailable
    _cg_build_ctx = None  # type: ignore
    _cg_render = None  # type: ignore

logger = logging.getLogger(__name__)


def _extract_json_payload(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = text[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


class ReportServiceError(Exception):
    """Base class for service-layer errors."""

    status_code: int = 500

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ReportNotFoundError(ReportServiceError):
    status_code = 404


class ReportAccessDeniedError(ReportServiceError):
    status_code = 403


class ReportNotReadyError(ReportServiceError):
    status_code = 409


class ReportDataValidationError(ReportServiceError):
    status_code = 500


@dataclass(slots=True)
class ReportServiceConfig:
    community_members: dict[str, int]
    cache_ttl_seconds: int
    target_analysis_version: str


class ReportCacheProtocol(Protocol):
    async def get(self, key: str) -> ReportPayload | None:
        ...

    async def set(self, key: str, value: ReportPayload) -> None:
        ...

    async def invalidate(self, key: str) -> None:
        ...


class InMemoryReportCache(ReportCacheProtocol):
    def __init__(self, ttl_seconds: int) -> None:
        self._ttl_seconds = max(1, ttl_seconds)
        self._store: dict[str, tuple[float, ReportPayload]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> ReportPayload | None:
        async with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            expires_at, payload = entry
            if expires_at <= time.monotonic():
                self._store.pop(key, None)
                return None
            return payload.model_copy(deep=True)

    async def set(self, key: str, value: ReportPayload) -> None:
        async with self._lock:
            self._store[key] = (
                time.monotonic() + self._ttl_seconds,
                value.model_copy(deep=True),
            )

    async def invalidate(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)


class ReportService:
    """Business logic for assembling the report analysis payload."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        config: ReportServiceConfig | None = None,
        cache: ReportCacheProtocol | None = None,
        repository: ReportRepository | None = None,
    ) -> None:
        resolved_config = config or ReportServiceConfig(
            community_members=settings.report_community_members,
            cache_ttl_seconds=settings.report_cache_ttl_seconds,
            target_analysis_version=settings.report_target_analysis_version,
        )
        self._config = resolved_config
        self._repository = repository or ReportRepository(db)
        self._cache = cache or InMemoryReportCache(resolved_config.cache_ttl_seconds)
        self._db = db

    def _get_quality_level(self) -> str:
        try:
            return str(getattr(settings, "report_quality_level", "standard")).strip().lower()
        except Exception:
            return "standard"

    async def _build_t1_market_report_md(self) -> tuple[str | None, T1StatsSnapshot | None, list[Any] | None, bool]:
        """生成 T1 市场版 Markdown；失败返回 None，不影响主流程。"""
        level = self._get_quality_level()
        if level not in {"standard", "premium"}:
            return None, None, None, False
        stats = await build_stats_snapshot(self._db)
        clusters = await build_pain_clusters(self._db)
        agent = T1MarketReportAgent(
            ReportInputs(
                stats=stats,
                clusters=clusters,
                product_description=getattr(settings, "report_product_description", "T1 市场报告"),
            ),
            quality_level=level,
        )
        md = await agent.render_async()
        return md, stats, clusters, agent.llm_used

    async def get_report(self, task_id: UUID, user_id: UUID) -> ReportPayload:
        task = await self._repository.get_task_with_analysis(task_id)
        if task is None:
            raise ReportNotFoundError("Task not found")

        if task.user_id != user_id:
            raise ReportAccessDeniedError("Not authorised to access this task")

        if task.status != TaskStatus.COMPLETED:
            raise ReportNotReadyError("Task has not completed yet")

        if task.analysis is None:
            raise ReportNotFoundError("Analysis not found")

        analysis = task.analysis
        if analysis.report is None:
            raise ReportNotFoundError("Report not found")

        user_membership = (
            task.user.membership_level if task.user else MembershipLevel.FREE
        )
        if user_membership not in {MembershipLevel.PRO, MembershipLevel.ENTERPRISE}:
            raise ReportAccessDeniedError(
                "Your subscription tier does not include report access"
            )

        cache_key = f"report:{task_id}:{user_id}"
        if self._cache:
            cached = await self._cache.get(cache_key)
            if (
                cached is not None
                and cached.generated_at == analysis.report.generated_at
            ):
                logger.debug("Cache hit for report task %s", task_id)
                return cached

        # facts_v2 质量闸门：若已拦截/勘探，则不要再“硬生成”新版报告（避免绕过门禁）。
        raw_sources = getattr(analysis, "sources", None) or {}
        report_tier = ""
        analysis_blocked = ""
        try:
            report_tier = str((raw_sources or {}).get("report_tier") or "").strip()
            analysis_blocked = str((raw_sources or {}).get("analysis_blocked") or "").strip()
        except Exception:
            report_tier = ""
            analysis_blocked = ""
        blocked_by_quality_gate = report_tier in {"X_blocked", "C_scouting"} or analysis_blocked in {
            "quality_gate_blocked",
            "scouting_brief",
        }

        analysis_payload = self._validate_analysis_payload(analysis)

        from app.core.config import settings as _cfg
        inline_llm_enabled = bool(getattr(_cfg, "enable_report_inline_llm", False))

        structured_report = analysis_payload.sources.report_structured
        if not structured_report and inline_llm_enabled and not blocked_by_quality_gate:
            try:
                facts_slice = getattr(analysis_payload.sources, "facts_slice", None)
                api_key = str(getattr(_cfg, "openai_api_key", "")).strip()
                if (
                    facts_slice
                    and getattr(_cfg, "enable_llm_summary", True)
                    and str(getattr(_cfg, "llm_model_name", "local-extractive")).strip()
                    != "local-extractive"
                    and api_key
                ):
                    facts_text = format_facts_for_prompt(facts_slice)
                    prompt = build_report_structured_prompt_v9(
                        task.product_description, facts_text
                    )
                    client = OpenAIChatClient(
                        model=getattr(_cfg, "llm_model_name", "gpt-4o-mini"),
                        timeout=60.0,
                        api_key=api_key,
                    )
                    raw = await client.generate(prompt, max_tokens=4000, temperature=0.25)
                    structured_report = _extract_json_payload(raw)
            except Exception:
                structured_report = None
        if structured_report:
            analysis_payload.sources.report_structured = structured_report

        # LLM Normalizer：对 competitor 名称做轻归一化（RAG 候选集：品牌+竞品+词典）
        # 质量闸门拦截/勘探时，直接跳过（避免无意义的 LLM/耗时分支）
        normalization_rate = 0.0
        if not blocked_by_quality_gate and inline_llm_enabled:
            try:
                candidates: list[str] = []
                try:
                    brands = getattr(analysis_payload.insights.entity_summary, "brands", [])
                    for row in brands or []:
                        name = getattr(row, "name", None) or (row.get("name") if isinstance(row, dict) else None)
                        if name:
                            candidates.append(str(name))
                except Exception:
                    pass
                competitors_raw = analysis_payload.insights.competitors or []
                for comp in competitors_raw:
                    name = getattr(comp, "name", None)
                    if name:
                        candidates.append(str(name))
                # 从实体词典补充候选（canonical 列）
                try:
                    from pathlib import Path as _Path
                    import csv as _csv
                    dict_path = None
                    for p in [
                        _Path("backend/config/entity_dictionary/crossborder_v2.csv"),
                        _Path("backend/config/entity_dictionary/crossborder_v2_balanced.csv"),
                        _Path("backend/config/entity_dictionary/crossborder_v2_conservative.csv"),
                        _Path("backend/config/entity_dictionary/crossborder_v2_aggressive.csv"),
                    ]:
                        if p.exists():
                            dict_path = p
                            break
                    if dict_path is not None:
                        with dict_path.open("r", encoding="utf-8") as fh:
                            reader = _csv.DictReader(fh)
                            for row in reader:
                                canon = (row.get("canonical") or "").strip()
                                if canon:
                                    candidates.append(canon)
                except Exception:
                    pass
                candidates = sorted({c.strip(): None for c in candidates if c}.keys())

                if candidates:
                    # 限制候选上限，避免 prompt 过大
                    CAPPED = candidates[:200]
                    norm_via = "local"
                    THRESH = 0.6

                    def _normalize_conf(s: str) -> tuple[str | None, float]:
                        return (None, 0.0)

                    if getattr(_cfg, "enable_llm_summary", True) and getattr(_cfg, "llm_model_name", "local-extractive") != "local-extractive":
                        try:
                            _norm = OpenAIRagConfidenceNormalizer(getattr(_cfg, "llm_model_name", "gpt-4o-mini"))
                            norm_via = "openai"

                            def _normalize_conf(s: str) -> tuple[str | None, float]:  # type: ignore[no-redef]
                                return _norm.normalize(s, candidates=CAPPED)
                        except Exception:
                            _local = LocalRagConfidenceNormalizer()

                            def _normalize_conf(s: str) -> tuple[str | None, float]:  # type: ignore[no-redef]
                                return _local.normalize(s, candidates=CAPPED)
                    else:
                        _local = LocalRagConfidenceNormalizer()

                        def _normalize_conf(s: str) -> tuple[str | None, float]:  # type: ignore[no-redef]
                            return _local.normalize(s, candidates=CAPPED)

                    total = 0
                    hits = 0
                    normalizations_data: list[dict] = []
                    for comp in competitors_raw:
                        try:
                            name = str(getattr(comp, "name", "") or "").strip()
                            if not name:
                                continue
                            total += 1
                            mapped, conf = _normalize_conf(name)
                            accepted = bool(mapped and mapped != name and conf >= THRESH)
                            if accepted:
                                comp.name = mapped  # type: ignore[attr-defined]
                                hits += 1
                            normalizations_data.append({
                                "original": name,
                                "mapped": mapped or name,
                                "confidence": round(conf, 3),
                                "accepted": accepted,
                                "via": norm_via,
                                "candidates": len(CAPPED),
                            })
                        except Exception:
                            continue
                    normalization_rate = (hits / total) if total > 0 else 0.0
            except Exception:
                normalization_rate = 0.0

        action_items = analysis_payload.insights.action_items
        if not action_items:
            generated = build_opportunity_reports(
                analysis_payload.insights.model_dump(mode="json")
            )
            action_items = [
                OpportunityReportOut.model_validate(item.to_dict())
                for item in generated
            ]

        def _clone_action_item(
            base: OpportunityReportOut, **updates: Any
        ) -> OpportunityReportOut:
            data = base.model_dump()
            data.update(updates)
            return OpportunityReportOut(**data)

        # P1: 证据密度约束（每条行动项至少2条可点击证据URL），不足则降级标注
        insufficient_evidence_detected = False
        normalized_items: list[OpportunityReportOut] = []
        for item in action_items:
            try:
                url_count = sum(
                    1 for ev in (item.evidence_chain or []) if getattr(ev, "url", None)
                )
                if url_count < 2:
                    insufficient_evidence_detected = True
                    # 降级标注（不改变结构，只追加一条提示到建议动作）
                    tips = list(item.suggested_actions or [])
                    marker = "证据不足(n<2)"
                    if marker not in tips:
                        tips.append(marker)
                    item = _clone_action_item(item, suggested_actions=tips)
            except Exception:
                pass
            normalized_items.append(item)

        # LLM 增益：证据要点句（模块化，可回退）
        # 质量闸门拦截/勘探时跳过（避免绕过门禁、也避免不必要的外部调用）
        if not blocked_by_quality_gate and inline_llm_enabled:
            try:
                summarizer = None
                if getattr(_cfg, "enable_llm_summary", True) and getattr(_cfg, "llm_model_name", "local-extractive") != "local-extractive":
                    try:
                        from app.services.llm.openai_summarizer import OpenAISummarizer as _OpenAISummarizer
                        summarizer = _OpenAISummarizer(
                            model=getattr(_cfg, "llm_model_name", "gpt-4o-mini")
                        )
                    except Exception:
                        summarizer = None
                if summarizer is None:
                    summarizer = LocalExtractiveSummarizer()

                transformed: list[OpportunityReportOut] = []
                from app.services.llm.interfaces import EvidenceText as _Ev

                for item in normalized_items:
                    evs = item.evidence_chain or []
                    evid_payload = [
                        _Ev(
                            title=str(getattr(ev, "title", "") or ""),
                            note=str(getattr(ev, "note", "") or ""),
                            url=getattr(ev, "url", None),
                        )
                        for ev in evs
                    ]
                    summaries = summarizer.summarize_evidences(
                        evid_payload, max_chars=28
                    )
                    # 回写到 note 字段，保留原 title
                    new_chain = []
                    for ev, summ in zip(evs, summaries):
                        try:
                            new_chain.append(
                                type(ev)(
                                    title=ev.title,
                                    url=ev.url,
                                    note=summ or (ev.note or ""),
                                )
                            )
                        except Exception:
                            new_chain.append(ev)
                    transformed.append(_clone_action_item(item, evidence_chain=new_chain))
                action_items = transformed
            except Exception:
                action_items = normalized_items
        else:
            action_items = normalized_items

        # LLM 增益：机会标题 + Slogan（失败回退；放入 suggested_actions 顶部）
        if not blocked_by_quality_gate and inline_llm_enabled:
            try:
                if getattr(_cfg, "enable_llm_summary", True) and getattr(_cfg, "llm_model_name", "local-extractive") != "local-extractive":
                    from app.services.llm.title_slogan import TitleSloganGenerator as _TS
                    gen = _TS(model=getattr(_cfg, "llm_model_name", "gpt-4o-mini"))
                    for idx, item in enumerate(action_items):
                        try:
                            opp = (
                                analysis_payload.insights.opportunities[idx]
                                if idx < len(analysis_payload.insights.opportunities)
                                else None
                            )
                            desc = item.problem_definition or (opp.description if opp else "")
                            title = gen.generate_title(desc)
                            slogan = gen.generate_slogan(desc)
                            sa = list(item.suggested_actions or [])
                            if title:
                                sa.insert(0, f"Title: {title}")
                            if slogan:
                                sa.insert(1 if title else 0, f"Slogan: {slogan}")
                            action_items[idx] = _clone_action_item(
                                item, suggested_actions=sa[: max(3, len(sa))]
                            )
                        except Exception:
                            continue
            except Exception:
                pass

        def _derive_action_title(text: str) -> str:
            if not text:
                return ""
            value = text.strip()
            for sep in ("。", "，", ".", ",", "；", ";", ":", "：", "-", "—"):
                if sep in value:
                    value = value.split(sep, 1)[0].strip()
                    break
            return value[:18] if len(value) > 18 else value

        for item in action_items:
            if not getattr(item, "category", None):
                item.category = "strategy"
            if not getattr(item, "title", None):
                extracted = None
                for action in item.suggested_actions or []:
                    if isinstance(action, str) and action.strip().startswith("Title:"):
                        extracted = action.split(":", 1)[1].strip()
                        break
                item.title = extracted or _derive_action_title(
                    item.problem_definition or ""
                ) or None

        # 机会规模二次校准：社群规模乘子（可调）
        try:
            from app.services.analysis.scoring_rules import ScoringRulesLoader
            loader = ScoringRulesLoader()
            rules = loader.load()
            est = getattr(rules, "opportunity_estimator", None)
            scale_weight = float(getattr(est, "scale_weight", 0.2) or 0.2)
            details = analysis_payload.sources.communities_detail or []
            avg_daily = 0.0
            try:
                if details:
                    vals = [float(getattr(d, "daily_posts", 0) or 0) for d in details if getattr(d, "daily_posts", None) is not None]
                    if vals:
                        avg_daily = sum(vals) / max(1, len(vals))
            except Exception:
                avg_daily = 0.0
            scale = avg_daily / (avg_daily + 50.0) if avg_daily > 0 else 0.0
            multiplier = max(0.8, min(2.0, 1.0 + scale_weight * scale))
            for opp in analysis_payload.insights.opportunities:
                try:
                    if getattr(opp, "potential_users_est", None) is not None:
                        val = int(getattr(opp, "potential_users_est"))
                        new_val = max(0, int(val * multiplier))
                        opp.potential_users_est = new_val  # type: ignore[attr-defined]
                        opp.potential_users = f"约{new_val}个潜在团队"  # type: ignore[attr-defined]
                except Exception:
                    continue
        except Exception:
            pass

        stats = self._build_stats(analysis_payload)
        overview = await self._build_overview(
            analysis_payload.sources.communities_detail or [], stats
        )
        summary = self._build_summary(
            analysis_payload.insights, analysis_payload.sources
        )
        market_health = self._build_market_health(
            analysis_payload.insights, analysis_payload.sources
        )
        # Build entity leaderboard (flattened from entity_summary) for frontend use
        entity_leaderboard: list[EntityLeaderboardItem] = []
        try:
            es = analysis_payload.insights.entity_summary
            for category in ("brands", "features", "pain_points", "channels", "logistics", "risks"):
                rows = getattr(es, category, [])
                for row in rows or []:
                    name = getattr(row, "name", None)
                    mentions = getattr(row, "mentions", 0) or 0
                    if isinstance(name, str):
                        entity_leaderboard.append(
                            EntityLeaderboardItem(name=name, category=category, mentions=max(0, int(mentions)))
                        )
            entity_leaderboard.sort(key=lambda x: x.mentions, reverse=True)
            entity_leaderboard = entity_leaderboard[:20]
        except Exception:
            entity_leaderboard = []
        metadata = self._build_metadata(
            task,
            analysis_payload,
            analysis.report.generated_at,
            stats,
        )

        # 统计一致性与降级标注：如 overview 百分比与 stats 总量不自洽，则记录 recovery 标记
        try:
            pct_sum = overview.sentiment.positive + overview.sentiment.negative + overview.sentiment.neutral
            # 允许四舍五入误差（±2）
            recovery_reasons: list[str] = []
            if pct_sum < 98 or pct_sum > 102:
                recovery_reasons.append("stats_inconsistency")
            if insufficient_evidence_detected:
                recovery_reasons.append("insufficient_evidence")
            if recovery_reasons:
                # 合并到 sources.recovery_strategy，便于前端或日志定位
                existing = (analysis_payload.sources.recovery_strategy or "").strip()
                merged = ",".join(filter(None, [existing] + recovery_reasons)).strip(",")
                analysis_payload.sources.recovery_strategy = merged or None
                metadata.recovery_applied = merged or None
        except Exception:
            # 保守处理，不影响主流程
            pass

        # 术语与措辞规范化（基于可选映射表），仅作用于可读文案，不改动原始数据统计
        def _normalize_text(s: Any) -> Any:
            if not isinstance(s, str):
                return s
            try:
                import yaml  # type: ignore
                from pathlib import Path
                mapping_file = Path("backend/config/phrase_mapping.yml")
                mapping: dict[str, str] = {}
                if mapping_file.exists():
                    mapping = yaml.safe_load(mapping_file.read_text(encoding="utf-8")) or {}
                for k, v in mapping.items():
                    s = s.replace(k, v)
            except Exception:
                # 忽略映射加载错误
                return s
            return s

        # 对 action_items 与 pain_points/opportunities 的可读字段做轻量规范化
        for item in action_items:
            try:
                if hasattr(item, "problem_definition") and item.problem_definition:
                    item.problem_definition = _normalize_text(item.problem_definition)
                if hasattr(item, "suggested_actions") and item.suggested_actions:
                    item.suggested_actions = [
                        _normalize_text(a) for a in item.suggested_actions
                    ]
            except Exception:
                continue

        for col in (analysis_payload.insights.pain_points, analysis_payload.insights.opportunities):
            for obj in col:
                try:
                    if hasattr(obj, "description") and obj.description:
                        obj.description = _normalize_text(obj.description)
                except Exception:
                    continue

        # Ensure example_posts contain absolute URLs for evidence linking
        for pain in analysis_payload.insights.pain_points:
            posts = getattr(pain, "example_posts", None) or []
            for post in posts:
                try:
                    if isinstance(post, dict):
                        raw_url = post.get("url") or ""
                        raw_pl = post.get("permalink") or ""
                        post["url"] = normalize_reddit_url(
                            url=str(raw_url or ""), permalink=str(raw_pl or "")
                        )
                    else:
                        raw_url = getattr(post, "url", None) or ""
                        raw_pl = getattr(post, "permalink", None) or ""
                        normalized = normalize_reddit_url(
                            url=str(raw_url or ""), permalink=str(raw_pl or "")
                        )
                        setattr(post, "url", normalized)
                except Exception:
                    continue

        def _coerce_report_html(raw: str | None) -> str:
            text = (raw or "").strip()
            if not text:
                return ""
            lowered = text.lower()
            if "<html" in lowered or "<body" in lowered or "<p" in lowered or "<h" in lowered:
                return text
            try:
                import markdown as _md  # type: ignore
                return _md.markdown(text, extensions=["extra", "tables"])
            except Exception:
                from html import escape as _escape
                return f"<pre>{_escape(text)}</pre>"

        def _render_structured_markdown(
            report_structured: Mapping[str, Any],
            *,
            product_description: str,
            facts_slice: Mapping[str, Any] | None,
            pain_points: Sequence[Any] | None,
        ) -> str:
            def _safe_text(value: Any) -> str:
                return str(value).strip() if value not in (None, "") else ""

            def _safe_list(value: Any) -> list[Any]:
                return list(value) if isinstance(value, list) else []

            def _fmt_lines(items: Sequence[str], indent: int = 0) -> list[str]:
                pad = " " * indent
                return [f"{pad}- {item}" for item in items if item]

            def _extract_volume() -> tuple[int, int]:
                aggregates = (facts_slice or {}).get("aggregates") or {}
                communities = aggregates.get("communities") or []
                posts_total = 0
                comments_total = 0
                if isinstance(communities, list):
                    for entry in communities:
                        if not isinstance(entry, dict):
                            continue
                        posts_total += int(entry.get("posts", 0) or 0)
                        comments_total += int(entry.get("comments", 0) or 0)
                return posts_total, comments_total

            def _collect_core_communities() -> list[str]:
                battlefields = _safe_list(report_structured.get("battlefields"))
                names: list[str] = []
                for bf in battlefields:
                    if not isinstance(bf, dict):
                        continue
                    subs = bf.get("subreddits") or []
                    for sub in subs:
                        sub_text = _safe_text(sub)
                        if sub_text and sub_text not in names:
                            names.append(sub_text)
                if names:
                    return names[:5]
                aggregates = (facts_slice or {}).get("aggregates") or {}
                communities = aggregates.get("communities") or []
                for entry in communities:
                    if not isinstance(entry, dict):
                        continue
                    name = _safe_text(entry.get("name"))
                    if name and name not in names:
                        names.append(name)
                return names[:5]

            def _extract_evidence_links(idx: int) -> list[str]:
                if not pain_points:
                    return []
                if idx >= len(pain_points):
                    return []
                entry = pain_points[idx]
                examples = getattr(entry, "example_posts", None) or []
                links: list[str] = []
                for post in examples:
                    url = None
                    text = None
                    if isinstance(post, dict):
                        url = post.get("url") or post.get("permalink")
                        text = post.get("content") or post.get("title")
                    else:
                        url = getattr(post, "url", None) or getattr(post, "permalink", None)
                        text = getattr(post, "content", None) or getattr(post, "title", None)
                    url_text = _safe_text(url)
                    if not url_text:
                        continue
                    text_value = _safe_text(text)
                    if text_value:
                        if len(text_value) > 60:
                            text_value = f"{text_value[:60]}..."
                        links.append(f"[{text_value}]({url_text})")
                    else:
                        links.append(url_text)
                return links[:2]

            decision_cards = _safe_list(report_structured.get("decision_cards"))
            market_health = report_structured.get("market_health") or {}
            battlefields = _safe_list(report_structured.get("battlefields"))
            pain_list = _safe_list(report_structured.get("pain_points"))
            drivers = _safe_list(report_structured.get("drivers"))
            opportunities = _safe_list(report_structured.get("opportunities"))

            core_communities = _collect_core_communities()
            posts_total, comments_total = _extract_volume()
            summary_parts = []
            for card in decision_cards:
                if not isinstance(card, dict):
                    continue
                if card.get("title") == "需求趋势":
                    summary_parts.append(_safe_text(card.get("conclusion")))
                if card.get("title") == "核心社群":
                    summary_parts.append(_safe_text(card.get("conclusion")))
            summary_line = "；".join([p for p in summary_parts if p])

            lines: list[str] = []
            lines.append("# 市场洞察报告")
            lines.append("")
            lines.append("## 顶部信息")
            lines.append(f"- 标题：{_safe_text(product_description)} · 市场洞察报告")
            if summary_line:
                lines.append(f"- 简述：{summary_line}")
            if core_communities:
                lines.append(f"- 核心社区：{', '.join(core_communities)}")
            lines.append("- 时间窗口：过去 12 个月")
            if posts_total or comments_total:
                lines.append(f"- 数据量级：约 {posts_total} 帖 / {comments_total} 评论")
            else:
                lines.append("- 数据量级：数据不足")
            lines.append("")
            lines.append("## 决策卡片")
            for card in decision_cards:
                if not isinstance(card, dict):
                    continue
                title = _safe_text(card.get("title")) or "要点"
                conclusion = _safe_text(card.get("conclusion"))
                details = [_safe_text(x) for x in _safe_list(card.get("details"))]
                lines.append(f"### {title}")
                if conclusion:
                    lines.append(f"- 结论：{conclusion}")
                if details:
                    lines.append("- 依据：")
                    lines.extend(_fmt_lines(details, indent=2))
                lines.append("")

            lines.append("## 概览（市场健康度诊断）")
            competition = market_health.get("competition_saturation") or {}
            ps_ratio = market_health.get("ps_ratio") or {}
            comp_level = _safe_text(competition.get("level"))
            comp_interp = _safe_text(competition.get("interpretation"))
            comp_details = [_safe_text(x) for x in _safe_list(competition.get("details"))]
            if comp_level or comp_interp or comp_details:
                lines.append("### 竞争饱和度")
                if comp_level:
                    lines.append(f"- 结论：{comp_level}")
                if comp_details:
                    lines.append("- 依据：")
                    lines.extend(_fmt_lines(comp_details, indent=2))
                if comp_interp:
                    lines.append(f"- 解读：{comp_interp}")
            ps_ratio_value = _safe_text(ps_ratio.get("ratio"))
            ps_conclusion = _safe_text(ps_ratio.get("conclusion"))
            ps_interp = _safe_text(ps_ratio.get("interpretation"))
            if ps_ratio_value or ps_conclusion or ps_interp:
                lines.append("### 难题与攻略比解读")
                if ps_ratio_value:
                    lines.append(f"- 比例：{ps_ratio_value}")
                if ps_conclusion:
                    lines.append(f"- 结论：{ps_conclusion}")
                if ps_interp:
                    lines.append(f"- 解读：{ps_interp}")
            lines.append("")

            lines.append("## 核心战场推荐（分社区画像）")
            for idx in range(4):
                entry = battlefields[idx] if idx < len(battlefields) else None
                label = f"战场 {idx + 1}"
                if not isinstance(entry, dict):
                    lines.append(f"### {label}（数据不足，暂无覆盖）")
                    lines.append("")
                    continue
                name = _safe_text(entry.get("name")) or label
                subreddits = [_safe_text(x) for x in _safe_list(entry.get("subreddits")) if _safe_text(x)]
                profile = _safe_text(entry.get("profile"))
                pains = [_safe_text(x) for x in _safe_list(entry.get("pain_points")) if _safe_text(x)]
                strategy = _safe_text(entry.get("strategy_advice"))
                lines.append(f"### {label}：{name}")
                if subreddits:
                    lines.append(f"- 相关社区：{', '.join(subreddits)}")
                if profile:
                    lines.append(f"- 人群画像：{profile}")
                if pains:
                    lines.append("- 核心吐槽点：")
                    lines.extend(_fmt_lines(pains, indent=2))
                if strategy:
                    lines.append(f"- 进入策略：{strategy}")
                lines.append("")

            lines.append("## 用户痛点（3 个）")
            for idx, item in enumerate(pain_list[:3], start=1):
                if not isinstance(item, dict):
                    continue
                title = _safe_text(item.get("title")) or f"痛点 {idx}"
                voices = [_safe_text(x) for x in _safe_list(item.get("user_voices")) if _safe_text(x)]
                impression = _safe_text(item.get("data_impression"))
                interpretation = _safe_text(item.get("interpretation"))
                lines.append(f"### {idx}. {title}")
                if voices:
                    lines.append("- 用户原声：")
                    lines.extend(_fmt_lines(voices, indent=2))
                if impression:
                    lines.append(f"- 数据印象：{impression}")
                if interpretation:
                    lines.append(f"- 解读：{interpretation}")
                evidence = _extract_evidence_links(idx - 1)
                if evidence:
                    lines.append("- 证据链接：")
                    lines.extend(_fmt_lines(evidence, indent=2))
                lines.append("")

            lines.append("## Top 购买驱动力")
            for item in drivers[:3]:
                if not isinstance(item, dict):
                    continue
                title = _safe_text(item.get("title"))
                description = _safe_text(item.get("description"))
                if title:
                    lines.append(f"- {title}：{description}" if description else f"- {title}")
            lines.append("")

            lines.append("## 商业机会（机会卡）")
            for idx, item in enumerate(opportunities[:2], start=1):
                if not isinstance(item, dict):
                    continue
                title = _safe_text(item.get("title")) or f"机会 {idx}"
                target_pains = [_safe_text(x) for x in _safe_list(item.get("target_pain_points")) if _safe_text(x)]
                target_communities = [
                    _safe_text(x) for x in _safe_list(item.get("target_communities")) if _safe_text(x)
                ]
                positioning = _safe_text(item.get("product_positioning"))
                selling_points = [
                    _safe_text(x) for x in _safe_list(item.get("core_selling_points")) if _safe_text(x)
                ]
                lines.append(f"### 机会卡 {idx}：{title}")
                if target_pains:
                    lines.append(f"- 痛点：{', '.join(target_pains)}")
                if target_communities:
                    lines.append(f"- 目标社群：{', '.join(target_communities)}")
                if positioning:
                    lines.append(f"- 产品定位：{positioning}")
                if selling_points:
                    lines.append("- 卖点：")
                    lines.extend(_fmt_lines(selling_points, indent=2))
                lines.append("")

            return "\n".join(lines).strip()

        structured_markdown: str | None = None
        if analysis_payload.sources.report_structured:
            structured_markdown = _render_structured_markdown(
                analysis_payload.sources.report_structured,
                product_description=analysis_payload.sources.product_description
                or task.product_description,
                facts_slice=analysis_payload.sources.facts_slice,
                pain_points=analysis_payload.insights.pain_points,
            )

        report_html_content = _coerce_report_html(
            structured_markdown or (analysis.report.html_content if analysis.report else "")
        )
        use_controlled_html = not bool(report_html_content)

        # Controlled Executive Summary v2 (Markdown) — non-fatal best-effort
        controlled_md: str | None = None
        metrics_data: dict[str, Any] = {}
        try:
            if _cg_build_ctx and _cg_render and not blocked_by_quality_gate:
                analysis_dict = {
                    "insights": analysis_payload.insights.model_dump(mode="json"),
                    "sources": analysis_payload.sources.model_dump(mode="json"),
                }
                # Default resources; allow absence without failure (env overridable)
                import os as _os

                def _candidate_paths(path: Path) -> list[Path]:
                    if path.is_absolute():
                        return [path]
                    parts = path.parts
                    if parts and parts[0] == "backend":
                        return [path, Path(*parts[1:])]
                    return [path, Path("backend") / path]

                def _first_existing(path: Path) -> Path | None:
                    for candidate in _candidate_paths(path):
                        try:
                            if candidate.exists():
                                return candidate
                        except Exception:
                            continue
                    return None

                lex_path = _first_existing(
                    Path(
                        _os.getenv(
                            "SEMANTIC_LEXICON_PATH",
                            "backend/config/semantic_sets/crossborder_v2.1.yml",
                        )
                    )
                )
                metrics_path = _first_existing(
                    Path(
                        _os.getenv(
                            "SEMANTIC_METRICS_PATH",
                            "backend/reports/local-acceptance/metrics/metrics.json",
                        )
                    )
                )
                template_path = _first_existing(
                    Path("backend/config/report_templates/executive_summary_v2.md")
                )
                lex_data = {}
                try:
                    if lex_path is not None and lex_path.exists():
                        import json as _json  # local import
                        lex_data = _json.loads(lex_path.read_text(encoding="utf-8"))
                except Exception:
                    lex_data = {}
                try:
                    if metrics_path is not None and metrics_path.exists():
                        import json as _json  # local import
                        metrics_data = _json.loads(metrics_path.read_text(encoding="utf-8"))
                except Exception:
                    metrics_data = {}
                if template_path is not None and template_path.exists():
                    ctx, _ = _cg_build_ctx(analysis_dict, lex_data, metrics_data, task_id=str(task.id))
                    tmpl = template_path.read_text(encoding="utf-8")
                    controlled_md = _cg_render(tmpl, ctx)
        except Exception:
            controlled_md = None

        # Optional: T1 Market report (premium/standard). If available, override controlled_md.
        t1_market_md, t1_stats, t1_clusters, t1_llm_used = None, None, None, False
        if not blocked_by_quality_gate and inline_llm_enabled:
            try:
                t1_market_md, t1_stats, t1_clusters, t1_llm_used = await self._build_t1_market_report_md()
            except Exception:
                t1_market_md, t1_stats, t1_clusters, t1_llm_used = None, None, None, False
            if t1_market_md and use_controlled_html:
                controlled_md = t1_market_md
                try:
                    if metadata.market_enhancements is None:
                        metadata.market_enhancements = {}
                    metadata.market_enhancements["mode"] = "t1_market"
                    metadata.llm_used = metadata.llm_used or t1_llm_used or (self._get_quality_level() == "premium")
                except Exception:
                    pass

        # Optional metrics summary for frontend (non-breaking)
        metrics_summary = None
        try:
            from app.schemas.report_payload import MetricsSummary, LayerCoverageItem
            ms = None
            if 'metrics_data' in locals() and metrics_data:
                ec = metrics_data.get("entity_coverage", {}) or {}
                layers = metrics_data.get("layer_coverage", []) or []
                items: list[LayerCoverageItem] = []
                for entry in layers:
                    try:
                        items.append(
                            LayerCoverageItem(
                                layer=str(entry.get("layer")),
                                posts=int(entry.get("posts", 0) or 0),
                                hit_posts=int(entry.get("hit_posts", 0) or 0),
                                coverage=float(entry.get("coverage", 0.0) or 0.0),
                            )
                        )
                    except Exception:
                        continue
                ms = MetricsSummary(
                    overall=float(ec.get("overall", 0.0) or 0.0),
                    brands=float(ec.get("brands", 0.0) or 0.0),
                    pain_points=float(ec.get("pain_points", 0.0) or 0.0),
                    top10_unique_share=float(ec.get("top10_unique_share", 0.0) or 0.0),
                    layers=items,
                )
            metrics_summary = ms
        except Exception:
            metrics_summary = None

        # Convert Markdown → HTML for report_html to keep semantics consistent
        rendered_html: str | None = None
        if controlled_md and not blocked_by_quality_gate and use_controlled_html:
            try:
                import markdown as _md  # type: ignore
                rendered_html = _md.markdown(controlled_md, extensions=["extra", "tables"])
                metadata.llm_used = metadata.llm_used or t1_llm_used
            except Exception:
                # Fallback: minimal wrap
                from html import escape as _escape
                rendered_html = f"<pre>{_escape(controlled_md)}</pre>"

        payload = ReportPayload(
            task_id=task.id,
            status=task.status,
            generated_at=analysis.report.generated_at,
            product_description=analysis_payload.sources.product_description
            or task.product_description,
            report_structured=analysis_payload.sources.report_structured,
            report=ReportContent(
                executive_summary=summary,
                pain_points=analysis_payload.insights.pain_points,
                pain_clusters=analysis_payload.insights.pain_clusters,
                competitors=analysis_payload.insights.competitors,
                opportunities=analysis_payload.insights.opportunities,
                action_items=action_items,
                purchase_drivers=analysis_payload.insights.top_drivers,
                market_health=market_health,
                entity_summary=analysis_payload.insights.entity_summary,
                entity_leaderboard=entity_leaderboard,
                competitor_layers_summary=analysis_payload.insights.competitor_layers_summary,
                channel_breakdown=analysis_payload.insights.channel_breakdown,
            ),
            metadata=metadata,
            overview=overview,
            stats=stats,
            report_html=report_html_content or rendered_html or analysis.report.html_content,
            metrics_summary=metrics_summary,
        )

        logger.debug(
            "Generated report payload for task %s (status=%s)",
            task.id,
            task.status,
        )
        if self._cache:
            await self._cache.set(cache_key, payload)
        # 审计落盘（最佳努力，不影响主流程）
        try:
            import json as _json
            audit = {
                "task_id": str(task.id),
                "llm_model": metadata.llm_model,
                "normalization_rate": 0.0,
            }
            try:
                # 利用上方计算（若变量在作用域）
                audit["normalization_rate"] = round(normalization_rate, 3)  # type: ignore[name-defined]
            except Exception:
                pass
            try:
                # 标题/口号与要点句审计（轻量）
                audit_details = {}
                # normalizations_data
                audit_details["normalizations"] = normalizations_data  # type: ignore[name-defined]
                audit["details"] = audit_details
            except Exception:
                pass
            out = Path("backend/reports/local-acceptance") / f"llm-audit-{task.id}.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(_json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        return payload

    def _validate_analysis_payload(self, analysis: Any) -> AnalysisRead:
        raw_insights = copy.deepcopy(analysis.insights or {})
        raw_sources = copy.deepcopy(analysis.sources or {})
        (
            migrated_insights,
            migrated_sources,
            resolved_version,
        ) = self._apply_version_migrations(
            str(analysis.analysis_version), raw_insights, raw_sources
        )
        processed_insights = self._normalise_insights(migrated_insights)
        processed_sources = self._normalise_sources(migrated_sources)

        payload = {
            "id": analysis.id,
            "task_id": analysis.task_id,
            "insights": processed_insights,
            "sources": processed_sources,
            "confidence_score": analysis.confidence_score,
            "analysis_version": resolved_version,
            "created_at": analysis.created_at,
        }

        try:
            return AnalysisRead.model_validate(payload)
        except ValidationError as exc:
            logger.exception(
                "Analysis payload validation failed for analysis=%s", analysis.id
            )
            raise ReportDataValidationError(
                "Failed to validate analysis payload"
            ) from exc

    def _normalise_insights(self, insights: dict[str, Any]) -> dict[str, Any]:
        def _derive_title(description: str) -> str:
            if not description:
                return ""
            text = description.strip()
            for sep in ("。", "，", ".", ",", "；", ";", ":", "：", "-", "—"):
                if sep in text:
                    text = text.split(sep, 1)[0].strip()
                    break
            return text[:18] if len(text) > 18 else text

        pain_points = insights.get("pain_points") or []
        for item in pain_points:
            sentiment = float(item.get("sentiment_score", 0.0))
            # Clamp sentiment_score to [-1.0, 1.0] range
            item["sentiment_score"] = max(-1.0, min(1.0, sentiment))
            if not item.get("severity"):
                item["severity"] = self._classify_severity(sentiment)
            item.setdefault("example_posts", [])
            item.setdefault("user_examples", [])
            description = str(item.get("description") or "").strip()
            if description:
                item.setdefault("text", description)
                if not item.get("title"):
                    item["title"] = _derive_title(description)

        insights.setdefault("pain_points", pain_points)

        # Ensure pain cluster metrics respect schema constraints
        pain_clusters = insights.get("pain_clusters") or []
        for cluster in pain_clusters:
            for key in ("positive_mean", "negative_mean", "neutral_mean"):
                value = cluster.get(key)
                if isinstance(value, (int, float)):
                    cluster[key] = max(-1.0, min(1.0, float(value)))
            # 某些旧版分析会写出 score<-1 或 >1，这里一并裁剪
            for key in ("score", "relevance", "relevance_score"):
                if key in cluster and isinstance(cluster[key], (int, float)):
                    cluster[key] = max(-1.0, min(1.0, float(cluster[key])))
        insights["pain_clusters"] = pain_clusters
        competitors_raw = insights.get("competitors") or []
        competitors = assign_competitor_layers(competitors_raw)
        insights["competitors"] = competitors
        insights.setdefault("competitor_layers_summary", build_layer_summary(competitors))
        if not insights.get("channel_breakdown"):
            channels = []
            entity_summary = insights.get("entity_summary") or {}
            if isinstance(entity_summary, Mapping):
                channels = entity_summary.get("channels") or []
            if isinstance(channels, Mapping):
                channels = list(channels.values())
            if isinstance(channels, list):
                insights["channel_breakdown"] = [
                    {"name": row.get("name"), "mentions": row.get("mentions", 0)}
                    for row in channels[:5]
                    if isinstance(row, Mapping) and row.get("name")
                ]
            else:
                insights["channel_breakdown"] = []
        opportunities = insights.get("opportunities") or []
        for item in opportunities:
            if not isinstance(item, Mapping):
                continue
            description = str(item.get("description") or "").strip()
            if description:
                item.setdefault("text", description)
                if not item.get("title"):
                    item["title"] = _derive_title(description)
        insights["opportunities"] = opportunities
        insights.setdefault("action_items", insights.get("action_items") or [])
        insights.setdefault("pain_clusters", insights.get("pain_clusters") or [])

        summary = insights.get("competitor_layers_summary") or []
        if not isinstance(summary, list):
            summary = []
        if len(summary) < 2:
            needed = 2 - len(summary)
            used_layers = {str((entry or {}).get("layer")) for entry in summary if isinstance(entry, Mapping)}
            extras: list[dict[str, Any]] = []

            for comp in competitors:
                if len(extras) >= needed:
                    break
                layer = str(comp.get("layer") or "layer_auto").lower() or "layer_auto"
                if layer in used_layers:
                    continue
                extras.append(
                    {
                        "layer": layer,
                        "label": layer.title(),
                        "top_competitors": [
                            {
                                "name": str(comp.get("name") or ""),
                                "mentions": int(comp.get("mentions") or 0),
                                "sentiment": comp.get("sentiment"),
                            }
                        ],
                        "threats": str(
                            (comp.get("strengths") or [""])[0]
                            if isinstance(comp.get("strengths"), Sequence)
                            and not isinstance(comp.get("strengths"), (str, bytes))
                            and comp.get("strengths")
                            else ""
                        ),
                    }
                )
                used_layers.add(layer)

            while len(extras) < needed:
                filler_layer = f"layer_auto_{len(summary) + len(extras) + 1}"
                extras.append(
                    {
                        "layer": filler_layer,
                        "label": filler_layer.replace("_", " ").title(),
                        "top_competitors": [
                            {
                                "name": "Synthetic competitor",
                                "mentions": 0,
                                "sentiment": None,
                            }
                        ],
                        "threats": "",
                    }
                )
            if extras:
                summary.extend(extras[:needed])
        insights["competitor_layers_summary"] = summary

        current_summary = insights.get("entity_summary") or {}
        insights.setdefault(
            "entity_summary",
            {
                "brands": current_summary.get("brands", []),
                "features": current_summary.get("features", []),
                "pain_points": current_summary.get("pain_points", []),
            },
        )
        return insights

    @staticmethod
    def _classify_severity(sentiment_score: float) -> str:
        if sentiment_score <= -0.6:
            return "high"
        if sentiment_score <= -0.3:
            return "medium"
        return "low"

    def _normalise_sources(self, sources: dict[str, Any]) -> dict[str, Any]:
        allowed_keys = {
            "communities",
            "posts_analyzed",
            "cache_hit_rate",
            "ps_ratio",
            "analysis_duration_seconds",
            "reddit_api_calls",
            "collection_warnings",
            "product_description",
            "communities_detail",
            "recovery_strategy",
            "fallback_quality",
            "dedup_stats",
            "duplicates_summary",
            "seed_source",
            "data_source",
            "facts_slice",
            "report_structured",
        }
        filtered = {key: sources.get(key) for key in allowed_keys if key in sources}
        filtered.setdefault("communities", [])
        filtered.setdefault("posts_analyzed", 0)
        filtered.setdefault("cache_hit_rate", 0.0)
        filtered.setdefault("analysis_duration_seconds", None)
        filtered.setdefault("reddit_api_calls", None)
        filtered.setdefault("collection_warnings", [])
        filtered.setdefault("product_description", None)
        filtered.setdefault("communities_detail", [])
        filtered.setdefault("ps_ratio", None)
        filtered.setdefault("facts_slice", None)
        filtered.setdefault("report_structured", None)
        return filtered

    def _apply_version_migrations(
        self,
        version: str,
        insights: dict[str, Any],
        sources: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any], str]:
        current = self._format_analysis_version(version)
        target = self._format_analysis_version(self._config.target_analysis_version)
        migrations: dict[str, Any] = {
            "0.9": self._migrate_v09_to_v10,
        }

        visited: set[str] = set()
        updated_insights = insights
        updated_sources = sources

        while current in migrations and current != target and current not in visited:
            visited.add(current)
            migrator = migrations[current]
            logger.info("Migrating analysis payload from version %s", current)
            updated_insights, updated_sources, current = migrator(
                updated_insights, updated_sources
            )

        return updated_insights, updated_sources, current

    def _migrate_v09_to_v10(
        self, insights: dict[str, Any], sources: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any], str]:
        migrated_insights = copy.deepcopy(insights)
        for item in migrated_insights.get("pain_points", []) or []:
            sentiment = float(item.get("sentiment_score", 0.0))
            item.setdefault("severity", self._classify_severity(sentiment))
            item.setdefault("example_posts", [])
            item.setdefault("user_examples", [])

        migrated_sources = copy.deepcopy(sources)
        # Backward-compat: move float analysis_duration → int analysis_duration_seconds
        if "analysis_duration" in migrated_sources:
            if migrated_sources.get("analysis_duration_seconds") is None:
                try:
                    migrated_sources["analysis_duration_seconds"] = int(
                        round(float(migrated_sources["analysis_duration"]))
                    )
                except Exception:
                    migrated_sources["analysis_duration_seconds"] = None
            # remove legacy field to satisfy strict schema
            migrated_sources.pop("analysis_duration", None)

        return migrated_insights, migrated_sources, "1.0"

    def _build_stats(self, analysis: AnalysisRead) -> ReportStats:
        pain_points = analysis.insights.pain_points
        competitors = analysis.insights.competitors

        positive_mentions = sum(
            item.frequency for item in pain_points if item.sentiment_score > 0.05
        ) + sum(
            comp.mentions
            for comp in competitors
            if str(comp.sentiment).lower() == "positive"
        )
        negative_mentions = sum(
            item.frequency for item in pain_points if item.sentiment_score < -0.05
        ) + sum(
            comp.mentions
            for comp in competitors
            if str(comp.sentiment).lower() == "negative"
        )
        # 初始以 posts_analyzed 为参考，若不可信则回退到自洽口径
        neutral_candidates = analysis.sources.posts_analyzed - positive_mentions - negative_mentions
        neutral_mentions = max(0, neutral_candidates)

        # 强制总和自洽：total = pos + neg + neu
        pos = max(int(positive_mentions), 0)
        neg = max(int(negative_mentions), 0)
        neu = max(int(neutral_mentions), 0)
        total = pos + neg + neu

        # 如 posts_analyzed 明显小于 pos+neg，则记入恢复策略由上层标注
        return ReportStats(
            total_mentions=total,
            positive_mentions=pos,
            negative_mentions=neg,
            neutral_mentions=neu,
        )

    async def _get_community_member_count(self, community_name: str) -> int:
        """Get member count for a community from database or fallback to config.

        Args:
            community_name: Community name (e.g., 'r/startups')

        Returns:
            Member count (from DB, config, or default 100,000)
        """
        from sqlalchemy import select

        from app.models.community_cache import CommunityCache

        # Try to get from database first
        try:
            result = await self._repository._db.execute(
                select(CommunityCache.member_count).where(
                    CommunityCache.community_name == community_name
                )
            )
            member_count = result.scalar_one_or_none()

            if member_count is not None and member_count > 0:
                logger.debug(
                    f"Using DB member count for {community_name}: {member_count:,}"
                )
                return member_count
        except Exception as e:
            logger.warning(
                f"Failed to fetch member count from DB for {community_name}: {e}"
            )

        # Fallback to config
        config_count = self._config.community_members.get(community_name.lower())
        if config_count:
            logger.debug(
                f"Using config member count for {community_name}: {config_count:,}"
            )
            return config_count

        # Final fallback to default
        logger.debug(f"Using default member count for {community_name}: 100,000")
        return 100_000

    async def _build_overview(
        self,
        communities_detail: list[CommunitySourceDetail],
        stats: ReportStats,
    ) -> ReportOverview:
        total = max(stats.total_mentions, 1)
        # Calculate percentages and ensure they sum to 100
        positive_pct = stats.positive_mentions / total * 100
        negative_pct = stats.negative_mentions / total * 100
        neutral_pct = stats.neutral_mentions / total * 100

        # Round and clamp to ensure valid range [0, 100]
        positive = max(0, min(100, int(round(positive_pct))))
        negative = max(0, min(100, int(round(negative_pct))))
        neutral = max(0, min(100, int(round(neutral_pct))))

        # Adjust to ensure sum doesn't exceed 100
        total_pct = positive + negative + neutral
        if total_pct > 100:
            # Reduce the largest component
            if positive >= negative and positive >= neutral:
                positive -= (total_pct - 100)
            elif negative >= neutral:
                negative -= (total_pct - 100)
            else:
                neutral -= (total_pct - 100)

        sentiment = SentimentBreakdown(
            positive=max(0, positive),
            negative=max(0, negative),
            neutral=max(0, neutral),
        )

        # Build top communities with member counts from DB
        top_communities = []
        # 社区治理：过滤黑名单社区，避免噪音出现在 Top 列
        filtered_details = communities_detail
        try:
            from app.services.blacklist_loader import get_blacklist_config
            bl = get_blacklist_config()
            filtered_details = [d for d in communities_detail if not bl.is_community_blacklisted(d.name)] or communities_detail
        except Exception:
            filtered_details = communities_detail
        for detail in sorted(
            filtered_details,
            key=lambda item: item.mentions,
            reverse=True,
        )[:5]:
            member_count = await self._get_community_member_count(detail.name)
            top_communities.append(
                TopCommunity(
                    name=detail.name,
                    mentions=detail.mentions,
                    relevance=int(round(detail.cache_hit_rate * 100)),
                    category=(detail.categories or [None])[0],
                    daily_posts=detail.daily_posts,
                    avg_comment_length=detail.avg_comment_length,
                    from_cache=detail.from_cache,
                    members=member_count,
                )
            )

        # Header helpers
        total_communities = len(communities_detail)
        top_n = len(top_communities)
        # 推断来源：若任一条 detail.categories 包含 "discovered"，认为来源包含 discovery
        seed_source = None
        try:
            if any("discovered" in (d.categories or []) for d in communities_detail):
                seed_source = "pool+discovery"
            elif communities_detail:
                seed_source = "pool"
        except Exception:
            seed_source = None

        return ReportOverview(
            sentiment=sentiment,
            top_communities=top_communities,
            total_communities=total_communities,
            top_n=top_n,
            seed_source=seed_source,
        )

    def _build_summary(
        self,
        insights: InsightsPayload,
        sources: SourcesPayload,
    ) -> ReportExecutiveSummary:
        key_insights = (
            len(insights.pain_points)
            + len(insights.competitors)
            + len(insights.opportunities)
        )
        top_opportunity = (
            insights.opportunities[0].description if insights.opportunities else ""
        )
        return ReportExecutiveSummary(
            total_communities=len(sources.communities),
            key_insights=key_insights,
            top_opportunity=top_opportunity,
        )

    def _build_market_health(
        self,
        insights: InsightsPayload,
        sources: SourcesPayload,
    ) -> MarketHealth | None:
        saturation_scores: list[float] = []
        for item in insights.market_saturation or []:
            try:
                score = float(getattr(item, "overall_saturation", None) or 0.0)
            except Exception:
                continue
            saturation_scores.append(max(0.0, min(1.0, score)))

        saturation_score = None
        if saturation_scores:
            saturation_score = sum(saturation_scores) / max(1, len(saturation_scores))

        saturation_level = None
        if saturation_score is not None:
            if saturation_score >= 0.7:
                saturation_level = "high"
            elif saturation_score <= 0.4:
                saturation_level = "low"
            else:
                saturation_level = "medium"

        ps_ratio_value = None
        try:
            facts_slice = sources.facts_slice or {}
            if isinstance(facts_slice, Mapping):
                for key in ("ps_ratio", "ps_ratio_value", "ps_ratio_mean"):
                    raw = facts_slice.get(key)
                    if isinstance(raw, (int, float)):
                        ps_ratio_value = float(raw)
                        break
            if ps_ratio_value is None:
                raw = getattr(sources, "ps_ratio", None)
                if isinstance(raw, (int, float)):
                    ps_ratio_value = float(raw)
        except Exception:
            ps_ratio_value = None

        ps_ratio_assessment = None
        if ps_ratio_value is not None:
            if 0.8 <= ps_ratio_value <= 1.2:
                ps_ratio_assessment = "healthy"
            else:
                ps_ratio_assessment = "imbalanced"

        if saturation_score is None and ps_ratio_value is None:
            return None

        return MarketHealth(
            saturation_level=saturation_level or "unknown",
            saturation_score=saturation_score,
            ps_ratio=ps_ratio_value,
            ps_ratio_assessment=ps_ratio_assessment
            or ("unknown" if ps_ratio_value is None else None),
        )

    def _build_metadata(
        self,
        task: Task,
        analysis: AnalysisRead,
        generated_at: Any,
        stats: ReportStats,
    ) -> ReportMetadata:
        processing_seconds = analysis.sources.analysis_duration_seconds
        if processing_seconds is None and generated_at is not None:
            processing_seconds = max(
                0.0,
                float((generated_at - analysis.created_at).total_seconds()),
            )

        fallback_quality = None
        if analysis.sources.fallback_quality:
            fallback_quality = FallbackQuality.model_validate(
                analysis.sources.fallback_quality
            )

        # LLM 审计（以分析侧标记为准，避免误报）
        llm_used = analysis.sources.llm_used
        llm_model = analysis.sources.llm_model
        llm_rounds = analysis.sources.llm_rounds
        if not llm_model:
            try:
                from app.core.config import settings as app_settings
                llm_model = getattr(app_settings, "llm_model_name", "local-extractive")
            except Exception:
                llm_model = "local-extractive"
        if llm_rounds is None:
            if llm_used is None:
                llm_rounds = None
            else:
                llm_rounds = 2 if llm_used else 0

        # 语义词库版本号（用于跨境主题追溯）：
        lexver: str | None = None
        try:
            import os as _os
            from pathlib import Path as _P
            # 允许外部显式指定
            env_ver = _os.getenv("SEMANTIC_LEXICON_VERSION")
            if env_ver and env_ver.strip():
                lexver = env_ver.strip()
            else:
                lex_path = _P(_os.getenv("SEMANTIC_LEXICON_PATH", "backend/config/semantic_sets/crossborder_v2.1.yml"))
                if lex_path.exists():
                    text = lex_path.read_text(encoding="utf-8")
                    # 优先尝试 JSON 解析（当前仓库的 .yml 实际为 JSON 结构）
                    try:
                        import json as _json
                        payload = _json.loads(text)
                        v = payload.get("version") if isinstance(payload, dict) else None
                        if isinstance(v, str) and v.strip():
                            lexver = v.strip()
                    except Exception:
                        # 回退：从文件名提取（如 crossborder_v2.1.yml → v2.1）
                        stem = lex_path.stem
                        # 简单提取：匹配包含 v 或 _ 的版本片段
                        for token in (stem.split("_") + stem.split("-")):
                            if token.lower().startswith("v") and any(ch.isdigit() for ch in token):
                                lexver = token
                                break
        except Exception:
            lexver = None

        return ReportMetadata(
            analysis_version=self._format_analysis_version(analysis.analysis_version),
            confidence_score=float(analysis.confidence_score or 0.0),
            processing_time_seconds=float(processing_seconds or 0.0),
            cache_hit_rate=float(analysis.sources.cache_hit_rate or 0.0),
            total_mentions=stats.total_mentions,
            recovery_applied=analysis.sources.recovery_strategy,
            fallback_quality=fallback_quality,
            llm_used=llm_used,
            llm_model=llm_model,
            llm_rounds=llm_rounds,
            lexicon_version=lexver,
        )

    @staticmethod
    def _format_analysis_version(version: Any) -> str:
        try:
            numeric = float(version)
        except (TypeError, ValueError):
            return str(version)
        if numeric.is_integer():
            return f"{numeric:.1f}"
        return str(numeric)


__all__ = [
    "InMemoryReportCache",
    "ReportAccessDeniedError",
    "ReportCacheProtocol",
    "ReportDataValidationError",
    "ReportNotFoundError",
    "ReportNotReadyError",
    "ReportService",
    "ReportServiceConfig",
    "ReportServiceError",
]
