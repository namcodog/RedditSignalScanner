import sys
import os
import asyncio
from sqlalchemy import text
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory

async def run_audit():
    # SessionFactory itself might not be awaitable if it just returns a session class, 
    # but the session methods ARE awaitable.
    # Usually SessionFactory() returns a session instance in these frameworks.
    session = SessionFactory()
    try:
        print("--- 📊 社区版图现状 (Community Verticals) ---")
        # Query 1: Verticals
        try:
            # We assume 'vertical' column exists based on the SQL file found earlier
            result = await session.execute(text("SELECT vertical, COUNT(*) FROM community_pool GROUP BY vertical ORDER BY count DESC"))
            rows = result.fetchall()
            for row in rows:
                v = row[0] if row[0] else "👻 未归类 (Unknown)"
                print(f"  • {v}: {row[1]} 个社区")
        except Exception as e:
            print(f"Error querying verticals: {e}")

        print("\n--- 📦 库存盘点 (Data Volume) ---")
        # Query 2: Total Posts
        try:
            result = await session.execute(text("SELECT COUNT(*) FROM posts_raw"))
            count = result.scalar()
            print(f"  • 原始帖子总数 (Posts Raw): {count}")
        except Exception as e:
            print(f"Error counting posts: {e}")

        print("\n--- 🏆 囤积大户 (Top 10 Subreddits) ---")
        # Query 3: Top Sources
        try:
            result = await session.execute(text("SELECT subreddit, COUNT(*) FROM posts_raw GROUP BY subreddit ORDER BY count DESC LIMIT 10"))
            rows = result.fetchall()
            for row in rows:
                print(f"  • {row[0]}: {row[1]} 条")
        except Exception as e:
             print(f"Error counting top subreddits: {e}")

    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(run_audit())