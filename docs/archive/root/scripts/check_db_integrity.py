import asyncio
import os
import sys
from sqlalchemy import text

# Ensure backend is in pythonpath
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.db.session import SessionFactory

async def check_integrity():
    print("🏥 Starting Database Health Check...\n")
    async with SessionFactory() as session:
        # 1. Community Pool Check
        print("--- 1. Community Pool Check ---")
        try:
            # Total Count
            res = await session.execute(text("SELECT COUNT(*) FROM community_pool"))
            total = res.scalar()
            print(f"✅ Total Communities: {total}")

            # Vertical Integrity
            res = await session.execute(text("SELECT COUNT(*) FROM community_pool WHERE vertical IS NULL"))
            null_vertical = res.scalar()
            if null_vertical > 0:
                print(f"⚠️  Communities with NULL vertical: {null_vertical}")
            else:
                print("✅ All communities have vertical assigned.")

            # Status Distribution
            print("\n📊 Status Distribution:")
            res = await session.execute(text("SELECT status, COUNT(*) FROM community_pool GROUP BY status"))
            for row in res.fetchall():
                print(f"   - {row[0]}: {row[1]}")

            # Vertical Distribution
            print("\n📊 Vertical Distribution:")
            res = await session.execute(text("SELECT vertical, COUNT(*) FROM community_pool GROUP BY vertical"))
            for row in res.fetchall():
                print(f"   - {row[0]}: {row[1]}")

        except Exception as e:
            print(f"❌ Community Pool Check Failed: {e}")

        # 2. Data Freshness Check
        print("\n--- 2. Data Freshness Check (posts_raw) ---")
        try:
            res = await session.execute(text("SELECT COUNT(*) FROM posts_raw"))
            total_posts = res.scalar()
            res = await session.execute(text("SELECT COUNT(*) FROM posts_raw WHERE created_at > NOW() - INTERVAL '30 days'"))
            recent_posts = res.scalar()
            print(f"✅ Total Posts: {total_posts}")
            print(f"✅ Posts in last 30 days: {recent_posts}")
        except Exception as e:
            print(f"❌ Posts Check Failed: {e}")

        # 3. Materialized Views Check
        print("\n--- 3. Materialized Views Check ---")
        views = ["mv_analysis_entities", "mv_analysis_labels", "posts_latest"]
        for view in views:
            try:
                res = await session.execute(text(f"SELECT COUNT(*) FROM {view}"))
                cnt = res.scalar()
                status = "✅ Populated" if cnt > 0 else "⚠️  EMPTY"
                print(f"{status} {view}: {cnt} rows")
            except Exception as e:
                print(f"❌ View {view} Check Failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_integrity())
