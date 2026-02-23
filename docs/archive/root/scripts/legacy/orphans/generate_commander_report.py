import asyncio
import os
import sys
import json
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Path Setup
CURRENT_FILE = os.path.abspath(__file__)
SCRIPTS_DIR = os.path.dirname(CURRENT_FILE)
BACKEND_DIR = os.path.dirname(SCRIPTS_DIR)
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")
if "postgresql+asyncpg" not in DATABASE_URL and "postgresql://" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

REPORT_FILE = os.path.join(BACKEND_DIR, "../reports/commander_report_20251214.md")

async def generate_report():
    print("🚀 Generating Battlefield Commander Report...")
    
    async with AsyncSessionLocal() as session:
        # 1. Community Assets (The Troops)
        print("   Fetching Community Stats...")
        res_comm = await session.execute(text("""
            SELECT name, core_post_ratio, recent_core_posts_30d, avg_value_score, tier
            FROM community_pool
            WHERE status = 'active'
            ORDER BY core_post_ratio DESC
            LIMIT 10
        """))
        top_communities = res_comm.fetchall()

        # 2. Core Intelligence (The Gold)
        print("   Fetching Top Signals...")
        # Get recent high-score posts (V2 Scores)
        res_signals = await session.execute(text("""
            SELECT p.title, p.subreddit, ps.value_score, ps.tags_analysis, ps.llm_version
            FROM post_scores ps
            JOIN posts_raw p ON ps.post_id = p.id
            WHERE ps.is_latest = TRUE
              AND ps.value_score >= 9.0
            ORDER BY p.created_at DESC
            LIMIT 10
        """))
        top_signals = res_signals.fetchall()

        # 3. Trends (The Weather)
        print("   Fetching Trends...")
        res_trends = await session.execute(text("""
            SELECT month_start, posts_cnt, comments_cnt, score_sum
            FROM mv_monthly_trend
            ORDER BY month_start DESC
            LIMIT 6
        """))
        trends = res_trends.fetchall()

        # 4. Audit Summary (The Black Box)
        print("   Fetching Audit Log...")
        res_audit = await session.execute(text("""
            SELECT event_type, count(*) as cnt
            FROM data_audit_events
            GROUP BY event_type
        """))
        audits = res_audit.fetchall()

    # --- Render Report ---
    with open(REPORT_FILE, "w") as f:
        f.write(f"# ⚔️ Reddit 战地指挥官报告 (Commander Report)\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**数据源**: V2 纯净架构 (Facts v2)\n\n")

        f.write("## 1. 兵力部署 (Community Assets)\n")
        f.write("目前战斗力最强的 Top 10 社区 (按含金量排序)：\n\n")
        f.write("| 社区 (Subreddit) | 核心贴占比 (Core Ratio) | 30天产出 (Output) | 平均分 (Avg Score) | 级別 |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")
        for c in top_communities:
            ratio = f"{float(c.core_post_ratio)*100:.1f}%" if c.core_post_ratio else "0%"
            f.write(f"| **{c.name}** | {ratio} | {c.recent_core_posts_30d} | {c.avg_value_score} | {c.tier} |\n")
        
        f.write("\n> **指挥官洞察**: 排名靠前的社区是我们的主战场，建议配置最高优先级的爬虫资源。\n\n")

        f.write("## 2. 核心情报 (Top Signals)\n")
        f.write("本周捕获的 10 个顶级商业信号 (Score >= 9.0)：\n\n")
        for s in top_signals:
            tags = s.tags_analysis if s.tags_analysis else {}
            pains = ", ".join(tags.get('pain_tags', [])) or "N/A"
            intent = tags.get('main_intent', 'N/A')
            f.write(f"### 🎯 [{s.value_score}] {s.title}\n")
            f.write(f"- **来源**: {s.subreddit}\n")
            f.write(f"- **意图**: `{intent}`\n")
            f.write(f"- **痛点**: {pains}\n")
            f.write(f"- **AI模型**: {s.llm_version}\n\n")

        f.write("## 3. 战场态势 (Trend Radar)\n")
        f.write("近 6 个月市场热度 (仅统计 Core/Lab 有效数据)：\n\n")
        f.write("| 月份 | 有效贴数 | 有效评论 | 热度总分 |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        for t in trends:
            f.write(f"| {t.month_start} | {t.posts_cnt} | {t.comments_cnt} | {t.score_sum} |\n")
        
        f.write("\n## 4. 系统健康 (System Health)\n")
        f.write("最近的自动审计记录：\n")
        for a in audits:
            f.write(f"- **{a.event_type}**: {a.cnt} 次\n")

    print(f"✅ Report generated: {REPORT_FILE}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(generate_report())
