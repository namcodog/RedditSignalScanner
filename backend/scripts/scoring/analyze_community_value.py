import argparse
import math
import os
import sys
from typing import Dict

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

# Ensure backend on path when executed from repo root
sys.path.append(os.path.join(os.getcwd(), "backend"))
sys.path.append(os.getcwd())

try:
    from app.core.config import get_settings
except Exception:
    get_settings = None


def compute_rfe_profile(stats_df: pd.DataFrame) -> pd.DataFrame:
    """
    纯计算：基于 total_posts / avg_engagement 生成 R-F-E 画像。

    输入列：subreddit, total_posts, avg_engagement, max_engagement, mvd (Phase 5.2)
    输出列：Subreddit, F, E, Max_Spike, MVD, Score, Archetype
    支持混合模型（0.3*year + 0.7*month）：当提供 f_year/f_month 列时使用混合频次，
    否则退化为 90 天窗口的频次计算。
    
    Phase 5.2: Score now includes MVD boost (MVD × 20).
    """
    df = stats_df.copy()

    # 填充缺失列，兼容测试数据
    if "subreddit" not in df.columns:
        df["subreddit"] = ""
    if "total_posts" not in df.columns:
        df["total_posts"] = 0
    if "avg_engagement" not in df.columns and "engagement" in df.columns:
        df["avg_engagement"] = df["engagement"]
    if "avg_engagement" not in df.columns:
        df["avg_engagement"] = 0.0
    if "max_engagement" not in df.columns:
        df["max_engagement"] = 0
    if "mvd" not in df.columns:
        df["mvd"] = 0.0

    # 混合频次：0.3 * f_year + 0.7 * f_month；若无则退化为 90 天频次
    if "f_year" in df.columns and "f_month" in df.columns:
        f_final = (0.3 * df["f_year"] + 0.7 * df["f_month"]).round(1)
    else:
        f_final = (df["total_posts"] / 90.0).round(1)

    df["F"] = f_final
    df["E"] = df["avg_engagement"].round(1)
    df["MVD"] = df["mvd"].round(2)
    
    # Phase 5.2: Score = E × log10(posts) + MVD × 20
    base_score = df["avg_engagement"] * df["total_posts"].add(1).apply(lambda x: math.log10(x) if x > 0 else 0.0)
    mvd_boost = df["mvd"] * 20  # MVD boost factor
    df["Score"] = (base_score + mvd_boost).round(1)
    df["Max_Spike"] = df["max_engagement"]

    def classify(row: pd.Series) -> str:
        if row["F"] >= 5.0:
            return "🔥 High Traffic"
        if row["E"] >= 50 and row["F"] < 2.0:
            return "💎 Hidden Gem"
        if row["E"] >= 20:
            return "⭐ Solid Gold"
        if row["F"] < 0.1 and row["E"] < 5.0:
            return "🧟 Zombie"
        return "🌱 Growing"

    df["Archetype"] = df.apply(classify, axis=1)
    return df[["subreddit", "F", "E", "MVD", "Max_Spike", "Score", "Archetype"]].rename(
        columns={"subreddit": "Subreddit"}
    )


def _freq_for(archetype: str) -> int:
    mapping = {
        "🔥 High Traffic": 2,
        "💎 Hidden Gem": 4,
        "⭐ Solid Gold": 6,
        "🌱 Growing": 12,
        "🧟 Zombie": 48,
    }
    return mapping.get(archetype, 12)


def analyze_community_value(apply_changes: bool = False) -> None:
    """
    R-F-E Profiling (90 天窗口), 可选写入 community_cache。
    """
    print("\n🔍 Starting R-F-E Analysis (Last 90 Days)...\n")

    # DB 连接
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/reddit_signal_scanner_dev",
    )
    if get_settings:
        try:
            settings = get_settings()
            db_url = settings.database_url.replace("asyncpg", "psycopg")
        except Exception:
            pass
    engine = create_engine(db_url, future=True)

    # 查询 365 天内的聚合 (支持混合模型)
    sql = text(
        """
        WITH stats AS (
            SELECT 
                subreddit,
                -- Year Stats
                COUNT(*) as posts_year,
                AVG(score + num_comments) as engagement_year,
                -- Month Stats
                COUNT(CASE WHEN created_at >= NOW() - INTERVAL '30 days' THEN 1 END) as posts_month,
                MAX(score + num_comments) as max_engagement
            FROM posts_raw
            WHERE 
                is_current = true 
                AND is_deleted = false
                AND created_at >= NOW() - INTERVAL '365 days'
            GROUP BY subreddit
        )
        SELECT 
            subreddit,
            posts_year as total_posts,
            engagement_year as avg_engagement,
            max_engagement,
            -- Pre-calculate frequencies for the python logic
            ROUND(posts_year / 365.0, 2) as f_year,
            ROUND(posts_month / 30.0, 2) as f_month
        FROM stats
        ORDER BY f_month DESC;
        """
    )
    
    # Phase 5.2: MVD (Maslow Value Density) 查询
    mvd_sql = text(
        """
        SELECT 
            pr.subreddit,
            COUNT(*) as total_labeled,
            COUNT(CASE WHEN psl.l1_category = 'Survival' THEN 1 END) as survival_cnt,
            COUNT(CASE WHEN psl.l1_category = 'Efficiency' THEN 1 END) as efficiency_cnt,
            COUNT(CASE WHEN psl.l1_category = 'Growth' THEN 1 END) as growth_cnt
        FROM posts_raw pr
        JOIN post_semantic_labels psl ON psl.post_id = pr.id
        WHERE pr.is_current = true AND pr.created_at >= NOW() - INTERVAL '365 days'
        GROUP BY pr.subreddit
        """
    )

    try:
        with engine.connect() as conn:
            stats_df = pd.read_sql(sql, conn)
            # Phase 5.2: Fetch MVD data
            mvd_df = pd.read_sql(mvd_sql, conn)
    except Exception as exc:
        print(f"❌ Analysis Failed (DB): {exc}")
        return

    if stats_df.empty:
        print("⚠️ No data found in the last 365 days.")
        return

    # Phase 5.2: Calculate MVD and merge
    # Weights from OpportunityScorer: Efficiency=2.5, Survival=1.5, Growth=1.2
    if not mvd_df.empty:
        mvd_df["mvd"] = (
            mvd_df["survival_cnt"] * 1.5 
            + mvd_df["efficiency_cnt"] * 2.5 
            + mvd_df["growth_cnt"] * 1.2
        ) / mvd_df["total_labeled"].replace(0, 1)  # Avoid div by zero
        mvd_df["mvd"] = mvd_df["mvd"].round(3)
        mvd_df = mvd_df[["subreddit", "mvd", "efficiency_cnt", "survival_cnt", "growth_cnt", "total_labeled"]]
        stats_df = stats_df.merge(mvd_df, on="subreddit", how="left")
        stats_df["mvd"] = stats_df["mvd"].fillna(0.0)
        print(f"📊 Phase 5.2: MVD data loaded for {len(mvd_df)} communities")
    else:
        stats_df["mvd"] = 0.0
        print("⚠️ Phase 5.2: No MVD data available (post_semantic_labels may be empty)")

    profile = compute_rfe_profile(stats_df).sort_values(by="Score", ascending=False)

    # 展示 Top 50
    pd.set_option("display.max_rows", 100)
    pd.set_option("display.width", 1000)
    pd.set_option('display.float_format', '{:.2f}'.format)
    
    print("🏆 Top 50 Communities (Hybrid Model):\n")
    print(profile.head(50).to_string(index=False))

    summary = profile["Archetype"].value_counts()
    print("\n📊 Archetype Distribution:")
    print(f"   - 🔥 High Traffic: {summary.get('🔥 High Traffic', 0)}")
    print(f"   - 💎 Hidden Gem: {summary.get('💎 Hidden Gem', 0)}")
    print(f"   - ⭐ Solid Gold: {summary.get('⭐ Solid Gold', 0)}")
    print(f"   - 🌱 Growing: {summary.get('🌱 Growing', 0)}")
    
    zombies = profile[profile['Archetype'] == '🧟 Zombie']
    if not zombies.empty:
        print(f"   - 🧟 Zombie: {len(zombies)}")
        print(f"\n⚠️  Found {len(zombies)} Zombie communities (purge recommended):")
        print(zombies[['Subreddit', 'F', 'E']].head(10).to_string(index=False))
    else:
        print("   - 🧟 Zombie: 0 (Clean Health)")

    if apply_changes:
        print("\n💾 Applying frequency updates to community_cache...")
        updated = 0
        with engine.begin() as conn:
            for _, row in profile.iterrows():
                freq = _freq_for(row["Archetype"])
                conn.execute(
                    text(
                        """
                        UPDATE community_cache
                        SET crawl_frequency_hours = :freq,
                            quality_tier = :tier,
                            updated_at = NOW()
                        WHERE community_name = :name
                        """
                    ),
                    {"freq": freq, "tier": "high", "name": row["Subreddit"]},
                )
                updated += 1
        print(f"✅ Updated schedules for {updated} communities.")
    else:
        print("\nℹ️ Run with --apply to write schedules to DB.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply calculated schedules to database")
    args = parser.parse_args()
    analyze_community_value(apply_changes=args.apply)
