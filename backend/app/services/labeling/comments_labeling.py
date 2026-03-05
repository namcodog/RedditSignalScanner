from __future__ import annotations

from typing import Iterable, Tuple

from sqlalchemy import delete, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import ContentLabel, ContentEntity, ContentType, EntityType
import os
import re
from app.services.semantic.text_classifier import classify_category_aspect
from pathlib import Path
from app.core.config import get_settings
from app.services.semantic.unified_lexicon import UnifiedLexicon


async def classify_and_label_comments(
    session: AsyncSession, reddit_comment_ids: Iterable[str]
) -> int:
    ids = [str(x) for x in reddit_comment_ids if x]
    if not ids:
        return 0
    from sqlalchemy import text as sqltext

    res = await session.execute(
        sqltext(
            "SELECT id, reddit_comment_id, body FROM comments WHERE reddit_comment_id = ANY(:ids)"
        ),
        {"ids": ids},
    )
    rows = list(res.mappings())
    if not rows:
        return 0

    comment_db_ids = [int(r["id"]) for r in rows]
    await session.execute(
        delete(ContentLabel).where(
            ContentLabel.content_type == ContentType.COMMENT.value,
            ContentLabel.content_id.in_(comment_db_ids),
        )
    )

    total = 0
    for r in rows:
        body = str(r["body"] or "")
        cls = classify_category_aspect(body)
        await session.execute(
            insert(ContentLabel).values(
                content_type=ContentType.COMMENT.value,
                content_id=int(r["id"]),
                category=cls.category.value,
                aspect=cls.aspect.value,
                sentiment_score=cls.sentiment_score,
                sentiment_label=cls.sentiment_label,
                confidence=90,
            )
        )
        total += 1
    return total


def _load_brand_patterns() -> Tuple[Tuple[str, EntityType], ...]:
    try:
        settings = get_settings()
        if getattr(settings, "enable_unified_lexicon", False):
            lexicon_path = Path(
                getattr(
                    settings,
                    "semantic_lexicon_path",
                    "backend/config/semantic_sets/unified_lexicon.yml",
                )
            )
            lex = UnifiedLexicon(lexicon_path)
            brands = [t.canonical for t in lex.get_brands()]
            return tuple((b.lower(), EntityType.BRAND) for b in brands[:500])
    except Exception:
        pass
    # fallback to old static patterns
    return (
        ("tonal", EntityType.BRAND),
        ("mirror", EntityType.BRAND),
        ("fiture", EntityType.BRAND),
        ("apple watch", EntityType.PLATFORM),
        ("peloton", EntityType.PLATFORM),
        ("fitbit", EntityType.PLATFORM),
    )


BRAND_PATTERNS: Tuple[Tuple[str, EntityType], ...] = _load_brand_patterns()

def _unified_enabled() -> bool:
    return os.getenv("ENABLE_UNIFIED_LEXICON", "false").strip().lower() in {"1", "true", "yes"}
_LEX_BRAND_PATS: list[tuple[str, re.Pattern[str]]] | None = None
_LEX_BRAND_MTIME: float | None = None

def _ensure_brand_patterns() -> None:
    global _LEX_BRAND_PATS
    if not _unified_enabled():
        return
    global _LEX_BRAND_MTIME
    try:
        from pathlib import Path
        from app.services.semantic.unified_lexicon import UnifiedLexicon

        cfg_path = os.getenv("SEMANTIC_LEXICON_PATH", "backend/config/semantic_sets/unified_lexicon.yml")
        p = Path(cfg_path)
        mtime = p.stat().st_mtime if p.exists() else None
        if _LEX_BRAND_PATS is not None and _LEX_BRAND_MTIME == mtime:
            return
        lex = UnifiedLexicon(p)
        brands = lex.get_brands()
        _LEX_BRAND_PATS = lex.get_patterns_for_matching(brands)
        _LEX_BRAND_MTIME = mtime
    except Exception:
        _LEX_BRAND_PATS = []


def _extract_entities_from_text(text: str) -> list[tuple[str, EntityType]]:
    t = (text or "").lower()
    out: list[tuple[str, EntityType]] = []
    if _unified_enabled():
        _ensure_brand_patterns()
        try:
            for name, pat in (_LEX_BRAND_PATS or []):
                if pat.search(t):
                    # 返回统一小写，便于断言与后续归一化
                    out.append((name.lower(), EntityType.BRAND))
        except Exception:
            pass
    else:
        for kw, et in BRAND_PATTERNS:
            if kw in t:
                out.append((kw, et))
    return out


async def extract_and_label_entities_for_comments(
    session: AsyncSession, reddit_comment_ids: Iterable[str]
) -> int:
    ids = [str(x) for x in reddit_comment_ids if x]
    if not ids:
        return 0
    from sqlalchemy import text as sqltext

    res = await session.execute(
        sqltext(
            "SELECT id, reddit_comment_id, body FROM comments WHERE reddit_comment_id = ANY(:ids)"
        ),
        {"ids": ids},
    )
    rows = list(res.mappings())
    if not rows:
        return 0

    comment_db_ids = [int(r["id"]) for r in rows]
    await session.execute(
        delete(ContentEntity).where(
            ContentEntity.content_type == ContentType.COMMENT.value,
            ContentEntity.content_id.in_(comment_db_ids),
        )
    )

    total = 0
    for r in rows:
        body = str(r["body"] or "")
        entities = _extract_entities_from_text(body)
        for name, et in entities:
            await session.execute(
                insert(ContentEntity).values(
                    content_type=ContentType.COMMENT.value,
                    content_id=int(r["id"]),
                    entity=name,
                    entity_type=et.value,
                    count=1,
                )
            )
            total += 1
    return total
