from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from sqlalchemy import select, text as sqltext
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.read_scopes import get_comments_core_lab_relation
from app.models.semantic_term import SemanticTerm
from app.repositories.semantic_candidate_repository import SemanticCandidateRepository
from app.services.semantic.unified_lexicon import UnifiedLexicon


# 3~4 token noun/专名短语，过滤数字/URL
_CANDIDATE_PATTERN = re.compile(
    r"\b([A-Za-z][A-Za-z0-9\-/]{3,30}(?:\s+[A-Za-z][A-Za-z0-9\-/]{2,30}){0,2})\b"
)
_URL = re.compile(r"https?://\S+|www\.\S+")
_NUM = re.compile(r"\d")
_STOPWORDS = {
    "reddit",
    "subreddit",
    "people",
    "thing",
    "something",
    "anything",
    "everything",
    "anyone",
    "everyone",
    "https",
    "http",
    "www",
    "com",
    "org",
    "net",
    "amp",
    "lol",
    "haha",
    "hey",
    "help",
    "idea",
    "thanks",
}


@dataclass(slots=True)
class CandidateTerm:
    canonical: str
    aliases: list[str]
    confidence: float
    evidence_post_ids: list[int]
    suggested_layer: str
    frequency: int
    first_seen: str


class CandidateExtractor:
    def __init__(self, lexicon: UnifiedLexicon, min_frequency: int = 5) -> None:
        self._lex = lexicon
        self._min_freq = max(1, int(min_frequency))
        self._min_similarity = 0.6  # 推荐阈值
        self._semantic_model = None
        self._seed_embeddings = None
        self._seed_terms: List[str] = self._build_seed_terms()

    # -------- Helpers --------
    def _build_seed_terms(self) -> List[str]:
        seeds: List[str] = []
        for t in self._lex.get_brands() + self._lex.get_features():
            seeds.append(t.canonical)
            seeds.extend(t.aliases or [])
        return [s for s in seeds if s]

    @staticmethod
    def _normalise_text(text: str) -> str:
        # 去 URL，压缩空白
        t = _URL.sub(" ", text)
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def _extract_terms(self, text: str) -> Iterable[str]:
        for m in _CANDIDATE_PATTERN.finditer(text):
            term = m.group(1).strip()
            if not term:
                continue
            if self._is_stopword(term):
                continue
            if _NUM.search(term):
                continue
            if not (4 <= len(term) <= 30):
                continue
            yield term

    def _is_stopword(self, term: str) -> bool:
        low = term.lower()
        if low in _STOPWORDS:
            return True
        return False

    def _semantic_similarity(self, term: str) -> float | None:
        """Best-effort 语义相似度，依赖 sentence-transformers；缺省返回 None。"""
        if not self._seed_terms:
            return None
        try:
            import numpy as np
            from sentence_transformers import SentenceTransformer  # type: ignore
        except Exception:
            return None
        if self._semantic_model is None:
            self._semantic_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            self._seed_embeddings = self._semantic_model.encode(
                self._seed_terms, normalize_embeddings=True
            )
        if self._seed_embeddings is None:
            return None
        emb = self._semantic_model.encode([term], normalize_embeddings=True)
        sims = np.dot(emb, self._seed_embeddings.T)[0]
        return float(np.max(sims))

    def _compute_confidence(self, freq: int, sim: float | None) -> float:
        freq_score = min(1.0, freq / max(self._min_freq, 1))
        sim_score = max(0.0, min(1.0, sim)) if sim is not None else 0.0
        conf = 0.4 + 0.35 * freq_score + 0.25 * sim_score
        return max(0.0, min(1.0, conf))

    # -------- Text-based (DB-agnostic) path for tests/tools --------
    def extract_from_texts(
        self, texts: Sequence[str], *, text_ids: Sequence[int] | None = None
    ) -> list[CandidateTerm]:
        """Extract candidates from plain texts (DB 无依赖，便于测试)。"""
        known = {
            t.canonical.lower()
            for t in (
                self._lex.get_brands()
                + self._lex.get_features()
                + self._lex.get_pain_points()
            )
        }
        out: Dict[str, Dict[str, object]] = {}
        ids_seq = list(text_ids) if text_ids is not None else list(range(len(texts)))
        for idx, raw in enumerate(texts):
            text_id = ids_seq[idx] if idx < len(ids_seq) else idx
            t = self._normalise_text(str(raw or ""))
            for term in self._extract_terms(t):
                low = term.lower()
                if len(term) < 3 or low in known:
                    continue  # skip known lexicon or too short
                rec = out.setdefault(
                    term,
                    {
                        "canonical": term,
                        "count": 0,
                        "ids": set(),
                        "cases": {term},
                        "first_seen": text_id,
                    },
                )
                rec["count"] = int(rec["count"]) + 1
                rec["ids"].add(int(text_id))
                rec["cases"].add(term)

        results: list[CandidateTerm] = []
        for term, rec in out.items():
            freq = int(rec["count"])  # type: ignore[assignment]
            if freq < self._min_freq:
                continue
            sim = self._semantic_similarity(term)
            if sim is not None and sim < self._min_similarity:
                continue  # 语义阈值过滤（仅在模型可用时）
            ids = sorted(int(x) for x in rec["ids"])  # type: ignore[arg-type]
            conf = self._compute_confidence(freq, sim)
            layer = self._suggest_layer(term)
            results.append(
                CandidateTerm(
                    canonical=term,
                    aliases=[],
                    confidence=round(conf, 3),
                    evidence_post_ids=ids,
                    suggested_layer=layer,
                    frequency=freq,
                    first_seen=str(rec["first_seen"]),  # type: ignore[arg-type]
                )
            )
        # 排序改为按频次优先，再按置信度，避免小样本被过度压制
        results.sort(key=lambda x: (-x.frequency, -x.confidence, x.canonical))
        return results

    # -------- DB path (best effort; optional) --------
    async def extract_from_db(
        self,
        session: AsyncSession,
        repository: SemanticCandidateRepository,
        *,
        lookback_days: int = 90,
        limit: int = 500,
    ) -> list[SemanticTerm]:
        """Extract from DB, persist candidates, and return DB-backed rows.

        - 优先用“痛点标签 + 品牌/功能共现”的评论（T1/T2 社区，score>0，非机器人）
        - 失败时回退 posts_hot（保持兼容）
        - Filter out terms already present in semantic_terms (lifecycle='approved').
        - Use bulk UPSERT to avoid N+1 INSERT/UPDATE patterns.
        """
        texts: list[str] = []
        text_ids: list[int] = []
        source = "comments"
        try:
            comments_rel = await get_comments_core_lab_relation(session)
            # 痛点×品牌/功能共现：T1/T2 社区 + pain 标签 + brand/feature 实体 + 非机器人 + 近 lookback_days
            q = sqltext(
                f"""
                SELECT
                    c.id AS comment_id,
                    COALESCE(c.body, '') AS text
                FROM {comments_rel} c
                JOIN community_pool cp
                    ON LOWER(REGEXP_REPLACE(cp.name, '^r/','')) = LOWER(REGEXP_REPLACE(c.subreddit, '^r/',''))
                JOIN content_labels l
                    ON l.content_type = 'comment'
                    AND l.content_id = c.id
                    AND l.category = 'pain'
                WHERE LOWER(cp.tier) IN ('t1', 't2', 'high', 'medium', 'semantic')
                  AND c.created_utc >= NOW() - INTERVAL ':days days'
                  AND c.score > 0
                  AND (c.author_name IS NULL OR c.author_name NOT ILIKE '%bot%')
                ORDER BY c.created_utc DESC
                LIMIT :limit
                """
            )
            res = await session.execute(
                q.bindparams(days=int(lookback_days), limit=int(limit))
            )
            rows = res.fetchall()
            texts = [str(row[1] or "") for row in rows]
            text_ids = [int(row[0]) for row in rows]
        except Exception:
            # 回退 posts_hot，保证兼容
            try:
                source = "posts"
                q2 = sqltext(
                    """
                    SELECT COALESCE(title,'') || ' ' || COALESCE(selftext,'') AS text, id
                    FROM posts_hot
                    WHERE created_at >= NOW() - INTERVAL ':days days'
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                )
                res = await session.execute(
                    q2.bindparams(days=int(lookback_days), limit=int(limit))
                )
                rows = res.fetchall()
                texts = [str(row[0] or "") for row in rows]
                text_ids = [int(row[1]) for row in rows]
            except Exception:
                texts = []
                text_ids = []
        if not texts:
            return []

        raw_candidates = self.extract_from_texts(texts, text_ids=text_ids)
        if not raw_candidates:
            return []

        # Filter out already-approved semantic terms
        existing_rows = await session.execute(
            select(SemanticTerm.canonical).where(SemanticTerm.lifecycle == "approved")
        )
        approved = {str(row[0]).lower() for row in existing_rows}
        filtered: list[CandidateTerm] = [
            c for c in raw_candidates if c.canonical.lower() not in approved
        ]
        if not filtered:
            return []

        term_freqs: list[Tuple[str, int]] = [
            (c.canonical, int(c.frequency)) for c in filtered
        ]
        persisted = await repository.bulk_upsert(term_freqs, source=source)
        return persisted

    # -------- Export --------
    def export_to_csv(self, candidates: list[CandidateTerm], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                [
                    "canonical",
                    "aliases",
                    "confidence",
                    "evidence_post_ids",
                    "suggested_layer",
                    "frequency",
                    "first_seen",
                ]
            )
            for c in candidates:
                writer.writerow(
                    [
                        c.canonical,
                        "|".join(c.aliases),
                        f"{c.confidence:.2f}",
                        ";".join(str(x) for x in c.evidence_post_ids),
                        c.suggested_layer,
                        c.frequency,
                        c.first_seen,
                    ]
                )

    # -------- Heuristics --------
    @staticmethod
    def _suggest_layer(term: str) -> str:
        low = term.lower()
        if any(x in low for x in ("shop", "platform", "amazon", "etsy", "temu", "shein", "tiktok")):
            return "L1"
        if any(x in low for x in ("ads", "ad", "dropshipping", "fba", "listing")):
            return "L2"
        if any(x in low for x in ("tool", "keyword", "analytics", "spider", "crawler")):
            return "L3"
        return "L1"


__all__ = ["CandidateExtractor", "CandidateTerm"]
