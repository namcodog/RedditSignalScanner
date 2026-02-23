from __future__ import annotations

"""
Validation script for semantic-db-migration (Phase 7.3).

Usage:
    python backend/scripts/validate_semantic_migration.py

Checks (read-only):
1. semantic_terms record count matches unified_lexicon.yml term count (if YAML exists)
2. All canonical terms in YAML exist in database
3. community_pool.semantic_quality_score is NOT NULL for all records
4. community_cache.crawl_quality_score is NOT NULL for all records
5. No orphan records in community_cache (all community_name reference community_pool.name)
6. comments.expires_at is set for all records
7. High-score comments (score>10 or awards_count>5) have expires_at >= created_utc + 180 days

Exit code:
    0 if all checks pass (or are explicitly skipped)
    1 if any check fails
"""

import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import yaml
from sqlalchemy import func, select, text

# Ensure backend/ is on sys.path when running as a standalone script
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionFactory
from app.models.comment import Comment
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.models.semantic_term import SemanticTerm


SEMANTIC_LEXICON_ENV = "SEMANTIC_LEXICON_PATH"
SEMANTIC_LEXICON_DEFAULT = "backend/config/semantic_sets/unified_lexicon.yml"


@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str


async def _load_yaml_terms() -> Tuple[List[str], str]:
    """Load canonical terms from unified_lexicon.yml if present.

    Returns (canonicals, info_message).
    """
    path_str = os.getenv(SEMANTIC_LEXICON_ENV, SEMANTIC_LEXICON_DEFAULT)
    path = Path(path_str)
    if not path.exists():
        return [], f"[SKIP] YAML file not found at {path}"

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        return [], f"[SKIP] Failed to parse YAML at {path}: {exc}"

    terms = payload.get("terms")
    if not isinstance(terms, list):
        return [], "[SKIP] YAML payload does not contain a 'terms' list; skipping semantic_terms checks"

    canonicals: List[str] = []
    for item in terms:
        if not isinstance(item, dict):
            continue
        canonical = item.get("canonical")
        if canonical:
            canonicals.append(str(canonical))
    return canonicals, f"[INFO] Loaded {len(canonicals)} canonical terms from {path}"


async def check_semantic_terms_match_yaml() -> List[CheckResult]:
    canonicals, info = await _load_yaml_terms()
    results: List[CheckResult] = []
    if not canonicals:
        # Nothing to validate; treat as informational skip
        results.append(CheckResult("C1_semantic_terms_vs_yaml", True, info))
        return results

    async with SessionFactory() as session:
        db_count = await session.scalar(
            select(func.count()).select_from(SemanticTerm)
        )
        yaml_count = len(canonicals)
        if db_count != yaml_count:
            results.append(
                CheckResult(
                    "C1_semantic_terms_vs_yaml",
                    False,
                    f"[FAIL] semantic_terms count mismatch: db={db_count}, yaml={yaml_count}",
                )
            )
        else:
            results.append(
                CheckResult(
                    "C1_semantic_terms_vs_yaml",
                    True,
                    f"[OK] semantic_terms count matches YAML: {db_count}",
                )
            )

        # Check that all YAML canonicals exist in DB
        missing: List[str] = []
        # chunk to avoid overly long IN lists
        chunk_size = 500
        for i in range(0, len(canonicals), chunk_size):
            chunk = canonicals[i : i + chunk_size]
            stmt = select(SemanticTerm.canonical).where(
                SemanticTerm.canonical.in_(chunk)
            )
            result = await session.execute(stmt)
            present = {row[0] for row in result.fetchall()}
            for c in chunk:
                if c not in present:
                    missing.append(c)

        if missing:
            sample = ", ".join(sorted(missing)[:10])
            results.append(
                CheckResult(
                    "C2_yaml_canonicals_exist",
                    False,
                    f"[FAIL] {len(missing)} YAML canonicals missing in semantic_terms, sample: {sample}",
                )
            )
        else:
            results.append(
                CheckResult(
                    "C2_yaml_canonicals_exist",
                    True,
                    "[OK] All YAML canonicals exist in semantic_terms",
                )
            )
    return results


async def check_quality_score_columns_not_null() -> List[CheckResult]:
    results: List[CheckResult] = []
    async with SessionFactory() as session:
        # community_pool.semantic_quality_score
        pool_missing = await session.scalar(
            select(func.count()).select_from(CommunityPool).where(
                CommunityPool.__table__.c.semantic_quality_score.is_(None)
            )
        )
        if pool_missing and pool_missing > 0:
            results.append(
                CheckResult(
                    "C3_pool_semantic_quality_not_null",
                    False,
                    f"[FAIL] community_pool.semantic_quality_score NULL count={pool_missing}",
                )
            )
        else:
            results.append(
                CheckResult(
                    "C3_pool_semantic_quality_not_null",
                    True,
                    "[OK] community_pool.semantic_quality_score is NOT NULL for all rows",
                )
            )

        # community_cache.crawl_quality_score
        cache_missing = await session.scalar(
            select(func.count()).select_from(CommunityCache).where(
                CommunityCache.__table__.c.crawl_quality_score.is_(None)
            )
        )
        if cache_missing and cache_missing > 0:
            results.append(
                CheckResult(
                    "C4_cache_crawl_quality_not_null",
                    False,
                    f"[FAIL] community_cache.crawl_quality_score NULL count={cache_missing}",
                )
            )
        else:
            results.append(
                CheckResult(
                    "C4_cache_crawl_quality_not_null",
                    True,
                    "[OK] community_cache.crawl_quality_score is NOT NULL for all rows",
                )
            )
    return results


async def check_community_cache_foreign_keys() -> CheckResult:
    async with SessionFactory() as session:
        # Ideally FK already enforces this; we still do an explicit scan for diagnostics.
        orphan_count = await session.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM community_cache c
                WHERE NOT EXISTS (
                    SELECT 1 FROM community_pool p WHERE p.name = c.community_name
                )
                """
            )
        )
    if orphan_count and orphan_count > 0:
        return CheckResult(
            "C5_cache_has_no_orphans",
            False,
            f"[FAIL] community_cache has {orphan_count} rows without matching community_pool.name",
        )
    return CheckResult(
        "C5_cache_has_no_orphans",
        True,
        "[OK] No orphan community_cache rows found",
    )


async def check_comments_ttl() -> List[CheckResult]:
    results: List[CheckResult] = []
    async with SessionFactory() as session:
        # expires_at should be set for all comments (work directly at SQL level to
        # avoid relying on ORM column definitions drifting from DB schema).
        missing_expires = await session.scalar(
            text("SELECT COUNT(*) FROM comments WHERE expires_at IS NULL")
        )
        if missing_expires and missing_expires > 0:
            results.append(
                CheckResult(
                    "C6_comments_expires_not_null",
                    False,
                    f"[FAIL] comments.expires_at NULL count={missing_expires}",
                )
            )
        else:
            results.append(
                CheckResult(
                    "C6_comments_expires_not_null",
                    True,
                    "[OK] comments.expires_at is set for all rows",
                )
            )

        # high-score comments should have TTL >= 180 days
        violating = await session.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM comments
                WHERE (score > 10 OR awards_count > 5)
                  AND expires_at IS NOT NULL
                  AND expires_at < created_utc + interval '180 days'
                """
            )
        )
    if violating and violating > 0:
        results.append(
            CheckResult(
                "C7_high_score_ttl_long_enough",
                False,
                f"[FAIL] {violating} high-score comments have TTL shorter than 180 days",
            )
        )
    else:
        results.append(
            CheckResult(
                "C7_high_score_ttl_long_enough",
                True,
                "[OK] High-score comments have TTL >= 180 days",
            )
        )
    return results


async def main() -> int:
    checks: List[CheckResult] = []

    checks.extend(await check_semantic_terms_match_yaml())
    checks.extend(await check_quality_score_columns_not_null())
    checks.append(await check_community_cache_foreign_keys())
    checks.extend(await check_comments_ttl())

    has_failure = False
    for res in checks:
        status = "PASS" if res.passed else "FAIL"
        print(f"[{status}] {res.name}: {res.message}")
        if not res.passed:
            has_failure = True

    if has_failure:
        print("\nSemantic DB migration validation: FAILED", file=sys.stderr)
        return 1

    print("\nSemantic DB migration validation: OK")
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted by user", file=sys.stderr)
        sys.exit(1)
    sys.exit(exit_code)
