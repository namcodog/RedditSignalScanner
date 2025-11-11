from __future__ import annotations

import asyncio
import copy
import logging
import time
from dataclasses import dataclass
from typing import Any, Protocol, Mapping
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.task import Task, TaskStatus
from app.models.user import MembershipLevel
from app.repositories.report_repository import ReportRepository
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
    ReportContent,
    ReportExecutiveSummary,
    ReportMetadata,
    ReportOverview,
    ReportPayload,
    ReportStats,
    SentimentBreakdown,
    TopCommunity,
)
from app.services.analysis import assign_competitor_layers, build_layer_summary
from app.services.reporting.opportunity_report import build_opportunity_reports
from app.services.llm.summarizer import LocalExtractiveSummarizer
from app.services.llm.normalizer import LocalDeterministicNormalizer
from app.services.llm.rag_conf_normalizer import (
    LocalRagConfidenceNormalizer,
    OpenAIRagConfidenceNormalizer,
)
from pathlib import Path

try:  # Optional import for controlled summary (Spec 011)
    from app.services.report.controlled_generator import build_context as _cg_build_ctx, render_report as _cg_render
except Exception:  # pragma: no cover - keep service resilient if module unavailable
    _cg_build_ctx = None  # type: ignore
    _cg_render = None  # type: ignore

logger = logging.getLogger(__name__)


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

        analysis_payload = self._validate_analysis_payload(analysis)

        # LLM Normalizer：对 competitor 名称做轻归一化（RAG 候选集：品牌+竞品+词典）
        normalization_rate = 0.0
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
                from app.core.config import settings as _cfg
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

        # P1: 证据密度约束（每条行动项至少2条可点击证据URL），不足则降级标注
        insufficient_evidence_detected = False
        normalized_items: list[OpportunityReportOut] = []
        for item in action_items:
            try:
                url_count = sum(1 for ev in (item.evidence_chain or []) if getattr(ev, "url", None))
                if url_count < 2:
                    insufficient_evidence_detected = True
                    # 降级标注（不改变结构，只追加一条提示到建议动作）
                    tips = list(item.suggested_actions or [])
                    marker = f"证据不足(n<2)"
                    if marker not in tips:
                        tips.append(marker)
                    item = OpportunityReportOut(
                        problem_definition=item.problem_definition,
                        evidence_chain=item.evidence_chain,
                        suggested_actions=tips,
                        confidence=item.confidence,
                        urgency=item.urgency,
                        product_fit=item.product_fit,
                        priority=item.priority,
                    )
            except Exception:
                pass
            normalized_items.append(item)
        # LLM 增益：证据要点句（模块化，可回退）
        try:
            from app.core.config import settings as _cfg
            summarizer = None
            if getattr(_cfg, "enable_llm_summary", True) and getattr(_cfg, "llm_model_name", "local-extractive") != "local-extractive":
                try:
                    from app.services.llm.openai_summarizer import OpenAISummarizer as _OpenAISummarizer
                    summarizer = _OpenAISummarizer(model=getattr(_cfg, "llm_model_name", "gpt-4o-mini"))
                except Exception:
                    summarizer = None
            if summarizer is None:
                summarizer = LocalExtractiveSummarizer()
            transformed: list[OpportunityReportOut] = []
            for item in normalized_items:
                evs = item.evidence_chain or []
                evid_texts = [
                    # 使用 title 作为主要素材，note 作为次要；URL 不进入摘要
                    # EvidenceItemOut: title, url, note
                    __import__("types") and __import__("typing") and __import__("builtins")  # no-op to placate linters
                ]
                # 构造轻量结构体以避免引入 Pydantic 依赖
                from app.services.llm.interfaces import EvidenceText as _Ev

                evid_payload = [_Ev(title=str(getattr(ev, "title", "") or ""), note=str(getattr(ev, "note", "") or ""), url=getattr(ev, "url", None)) for ev in evs]
                summaries = summarizer.summarize_evidences(evid_payload, max_chars=28)
                # 回写到 note 字段，保留原 title
                new_chain = []
                for ev, summ in zip(evs, summaries):
                    try:
                        new_chain.append(type(ev)(title=ev.title, url=ev.url, note=summ or (ev.note or "")))
                    except Exception:
                        new_chain.append(ev)
                transformed.append(
                    OpportunityReportOut(
                        problem_definition=item.problem_definition,
                        evidence_chain=new_chain,
                        suggested_actions=item.suggested_actions,
                        confidence=item.confidence,
                        urgency=item.urgency,
                        product_fit=item.product_fit,
                        priority=item.priority,
                    )
                )
            action_items = transformed
        except Exception:
            action_items = normalized_items

        # LLM 增益：机会标题 + Slogan（失败回退；放入 suggested_actions 顶部）
        try:
            from app.core.config import settings as _cfg
            if getattr(_cfg, "enable_llm_summary", True) and getattr(_cfg, "llm_model_name", "local-extractive") != "local-extractive":
                from app.services.llm.title_slogan import TitleSloganGenerator as _TS
                gen = _TS(model=getattr(_cfg, "llm_model_name", "gpt-4o-mini"))
                for idx, item in enumerate(action_items):
                    try:
                        opp = analysis_payload.insights.opportunities[idx] if idx < len(analysis_payload.insights.opportunities) else None
                        desc = item.problem_definition or (opp.description if opp else "")
                        title = gen.generate_title(desc)
                        slogan = gen.generate_slogan(desc)
                        sa = list(item.suggested_actions or [])
                        if title:
                            sa.insert(0, f"Title: {title}")
                        if slogan:
                            sa.insert(1 if title else 0, f"Slogan: {slogan}")
                        action_items[idx] = OpportunityReportOut(
                            problem_definition=item.problem_definition,
                            evidence_chain=item.evidence_chain,
                            suggested_actions=sa[: max(3, len(sa))],
                            confidence=item.confidence,
                            urgency=item.urgency,
                            product_fit=item.product_fit,
                            priority=item.priority,
                        )
                    except Exception:
                        continue
        except Exception:
            pass

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

        # Controlled Executive Summary v2 (Markdown) — non-fatal best-effort
        controlled_md: str | None = None
        try:
            if _cg_build_ctx and _cg_render:
                analysis_dict = {
                    "insights": analysis_payload.insights.model_dump(mode="json"),
                    "sources": analysis_payload.sources.model_dump(mode="json"),
                }
                # Default resources; allow absence without failure (env overridable)
                import os as _os
                lex_path = Path(_os.getenv("SEMANTIC_LEXICON_PATH", "backend/config/semantic_sets/crossborder_v2.1.yml"))
                metrics_path = Path(_os.getenv("SEMANTIC_METRICS_PATH", "backend/reports/local-acceptance/metrics/metrics.json"))
                template_path = Path("backend/config/report_templates/executive_summary_v2.md")
                lex_data = {}
                metrics_data = {}
                try:
                    if lex_path.exists():
                        import json as _json  # local import
                        lex_data = _json.loads(lex_path.read_text(encoding="utf-8"))
                except Exception:
                    lex_data = {}
                try:
                    if metrics_path.exists():
                        import json as _json  # local import
                        metrics_data = _json.loads(metrics_path.read_text(encoding="utf-8"))
                except Exception:
                    metrics_data = {}
                if template_path.exists():
                    ctx, _ = _cg_build_ctx(analysis_dict, lex_data, metrics_data, task_id=str(task.id))
                    tmpl = template_path.read_text(encoding="utf-8")
                    controlled_md = _cg_render(tmpl, ctx)
        except Exception:
            controlled_md = None

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
        if controlled_md:
            try:
                import markdown as _md  # type: ignore
                rendered_html = _md.markdown(controlled_md, extensions=["extra", "tables"])
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
            report=ReportContent(
                executive_summary=summary,
                pain_points=analysis_payload.insights.pain_points,
                pain_clusters=analysis_payload.insights.pain_clusters,
                competitors=analysis_payload.insights.competitors,
                opportunities=analysis_payload.insights.opportunities,
                action_items=action_items,
                entity_summary=analysis_payload.insights.entity_summary,
                entity_leaderboard=entity_leaderboard,
                competitor_layers_summary=analysis_payload.insights.competitor_layers_summary,
                channel_breakdown=analysis_payload.insights.channel_breakdown,
            ),
            metadata=metadata,
            overview=overview,
            stats=stats,
            report_html=rendered_html or analysis.report.html_content,
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
        pain_points = insights.get("pain_points") or []
        for item in pain_points:
            sentiment = float(item.get("sentiment_score", 0.0))
            # Clamp sentiment_score to [-1.0, 1.0] range
            item["sentiment_score"] = max(-1.0, min(1.0, sentiment))
            if not item.get("severity"):
                item["severity"] = self._classify_severity(sentiment)
            item.setdefault("example_posts", [])
            item.setdefault("user_examples", [])

        insights.setdefault("pain_points", pain_points)
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
        insights.setdefault("opportunities", insights.get("opportunities") or [])
        insights.setdefault("action_items", insights.get("action_items") or [])
        insights.setdefault("pain_clusters", insights.get("pain_clusters") or [])
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
        sources.setdefault("communities", [])
        sources.setdefault("posts_analyzed", 0)
        sources.setdefault("cache_hit_rate", 0.0)
        sources.setdefault("analysis_duration_seconds", None)
        sources.setdefault("reddit_api_calls", None)
        sources.setdefault("product_description", None)
        sources.setdefault("communities_detail", [])
        return sources

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

        # LLM 审计（模块化增益，失败回退但标记模型）
        llm_used = True
        try:
            from app.core.config import settings as app_settings
            llm_model = getattr(app_settings, "llm_model_name", "local-extractive")
        except Exception:
            llm_model = "local-extractive"
        llm_rounds = 1

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
