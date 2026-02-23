from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class BrandSaturation:
    brand: str
    saturation: float
    status: Literal["高饱和", "中等", "机会窗口"]


@dataclass
class CommunitySaturation:
    community: str
    brands: List[BrandSaturation]
    overall_saturation: float


class SaturationMatrix:
    """竞品饱和度矩阵：
    - 依据 posts_hot × content_entities(brand) 计算品牌在社区的被提及率
    - 分类：>0.6 高饱和，0.2-0.6 中等，<0.2 机会窗口
    """

    HIGH_TH: float = 0.6
    MID_TH: float = 0.2

    async def compute(
        self,
        session: AsyncSession,
        communities: Sequence[str],
        brands: Sequence[str],
        days: int | None = None,
    ) -> List[CommunitySaturation]:
        out: list[CommunitySaturation] = []
        # 既保留原始输入（用于输出展示），又准备lower版本（用于SQL匹配）
        targets = [c.lower().lstrip("r/") for c in communities]
        for i, sub in enumerate(targets):
            total_posts = await self._count_posts(session, sub, days=days)
            brand_counts = await self._get_brand_mentions(session, sub, days=days)

            rows: list[BrandSaturation] = []
            for b in brands:
                key = str(b)
                cnt = float(brand_counts.get(key, 0.0))
                denom = float(max(1, total_posts))
                sat = max(0.0, min(1.0, cnt / denom))
                rows.append(
                    BrandSaturation(brand=key, saturation=sat, status=self._classify_saturation(sat))
                )
            # 排序：饱和度降序
            rows.sort(key=lambda x: x.saturation, reverse=True)
            # overall：取前 5 的和（上限 1.0）
            overall = min(1.0, float(sum(r.saturation for r in rows[:5])))
            # 保留原始输入的社区名称（大小写/是否带 r/ 均按调用者传入）
            origin = communities[i] if i < len(communities) else f"r/{sub}"
            out.append(
                CommunitySaturation(
                    community=str(origin),
                    brands=rows,
                    overall_saturation=overall,
                )
            )
        return out

    async def _count_posts(self, session: AsyncSession, sub: str, days: int | None) -> int:
        res = await session.execute(
            text(
                """
                SELECT COUNT(*) FROM posts_hot WHERE lower(subreddit) IN (:r1, :r2)
                """
            ),
            {"r1": sub, "r2": f"r/{sub}"},
        )
        hot = int(res.scalar() or 0)
        if hot > 0 or not days:
            return hot
        res_raw = await session.execute(
            text(
                """
                SELECT COUNT(*) FROM posts_raw
                WHERE is_current = true
                  AND created_at >= NOW() - (interval '1 day' * :days)
                  AND lower(subreddit) IN (:r1, :r2)
                """
            ),
            {"r1": sub, "r2": f"r/{sub}", "days": days},
        )
        return int(res_raw.scalar() or hot)

    async def _get_brand_mentions(self, session: AsyncSession, community: str, days: int | None) -> Dict[str, int]:
        """统计品牌被提及的帖子数量（去重）。

        使用 content_entities(entity='BrandX', entity_type='brand', content_type='post')
        与 posts_hot 关联，计算每个 brand 在该社区被提及的不同 post 数量。
        """
        res = await session.execute(
            text(
                """
                WITH p AS (
                  SELECT id FROM posts_hot WHERE lower(subreddit) IN (:r1, :r2)
                )
                SELECT ce.entity AS brand, COUNT(DISTINCT ce.content_id) AS c
                FROM content_entities ce
                JOIN p ON p.id = ce.content_id
                WHERE ce.entity_type = 'brand' AND ce.content_type = 'post'
                GROUP BY ce.entity
                """
            ),
            {"r1": community, "r2": f"r/{community}"},
        )
        out: Dict[str, int] = {}
        for brand, c in res.fetchall():
            if brand:
                out[str(brand)] = int(c or 0)
        # Fallback to posts_raw if hot cache empty
        if out or not days:
            return out
        res_raw = await session.execute(
            text(
                """
                WITH p AS (
                  SELECT id FROM posts_raw 
                  WHERE is_current = true
                    AND created_at >= NOW() - (interval '1 day' * :days)
                    AND lower(subreddit) IN (:r1, :r2)
                )
                SELECT ce.entity AS brand, COUNT(DISTINCT ce.content_id) AS c
                FROM content_entities ce
                JOIN p ON p.id = ce.content_id
                WHERE ce.entity_type = 'brand' AND ce.content_type = 'post'
                GROUP BY ce.entity
                """
            ),
            {"r1": community, "r2": f"r/{community}", "days": days},
        )
        for brand, c in res_raw.fetchall():
            if brand:
                out[str(brand)] = int(c or 0)
        return out

    def _classify_saturation(self, value: float) -> Literal["高饱和", "中等", "机会窗口"]:
        v = float(value)
        if v >= self.HIGH_TH:
            return "高饱和"
        if v >= self.MID_TH:
            return "中等"
        return "机会窗口"

    async def compute_opportunity_windows(
        self,
        session: AsyncSession,
        *,
        communities: Sequence[str],
        brands: Sequence[str],
        low_threshold: float = 0.2,
        top_n: int = 5,
        days: int | None = None,
    ) -> Dict[str, List[Dict[str, float | str]]]:
        """为每个品牌挑出饱和度低的社区（机会窗口）。

        返回：{brand: [{community: 'r/X', saturation: 0.05, posts: 123}, ...]}
        排序：按 saturation 升序，posts 降序作为次序。
        """
        subs = [c.lower().lstrip("r/") for c in communities]
        origin_map: Dict[str, str] = {}
        for idx, sub in enumerate(subs):
            if idx < len(communities):
                origin_map[sub] = str(communities[idx])
        results: Dict[str, List[Dict[str, float | str]]] = {str(b): [] for b in brands}
        # 预取各社区总帖子数与品牌计数
        counts_cache: Dict[str, int] = {}
        mentions_cache: Dict[str, Dict[str, int]] = {}
        for sub in subs:
            counts_cache[sub] = await self._count_posts(session, sub, days=days)
            mentions_cache[sub] = await self._get_brand_mentions(session, sub, days=days)

        for brand in brands:
            rows: list[Dict[str, float | str]] = []
            for sub in subs:
                posts = float(counts_cache.get(sub, 0) or 0)
                if posts <= 0:
                    continue
                mentions = float(mentions_cache.get(sub, {}).get(str(brand), 0) or 0)
                sat = max(0.0, min(1.0, mentions / posts))
                if sat < float(low_threshold):
                    rows.append({
                        "community": origin_map.get(sub, f"r/{sub}"),
                        "saturation": sat,
                        "posts": int(posts),
                    })
            # 排序与截断
            rows.sort(key=lambda r: (float(r["saturation"]), -int(r["posts"])) )
            results[str(brand)] = rows[: max(1, int(top_n))]
        return results


__all__ = [
    "BrandSaturation",
    "CommunitySaturation",
    "SaturationMatrix",
]
