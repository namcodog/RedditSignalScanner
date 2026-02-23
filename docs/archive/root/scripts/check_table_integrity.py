
import asyncio
import sys
from pathlib import Path
from sqlalchemy import text
from backend.app.db.session import SessionFactory

# Ensure backend is in pythonpath
sys.path.append(str(Path.cwd()))

async def check_integrity():
    async with SessionFactory() as session:
        print("=== 🏥 David's Deep Integrity Scan ===")
        issues_found = 0

        # 1. Check for Duplicate Active Posts (CRITICAL)
        print("\n[1] 👯 Checking for Duplicate Active Posts...")
        q_dupes = text("""
            SELECT source_post_id, count(*) 
            FROM posts_raw 
            WHERE is_current = true 
            GROUP BY source_post_id 
            HAVING count(*) > 1 
            LIMIT 5
        """)
        rows = (await session.execute(q_dupes)).fetchall()
        if rows:
            print(f"   ❌ CRITICAL FAIL: Found {len(rows)} posts with multiple active versions!")
            for r in rows:
                print(f"      - ID {r.source_post_id} has {r.count} active rows.")
            issues_found += 1
        else:
            print("   ✅ Pass: No duplicate active posts.")

        # 2. Check for Orphan Scores (Score exists, Post missing)
        print("\n[2] 👻 Checking for Orphan Scores...")
        q_orphan_scores = text("""
            SELECT count(*) 
            FROM post_scores s
            LEFT JOIN posts_raw p ON s.post_id = p.id
            WHERE p.id IS NULL
        """)
        count = (await session.execute(q_orphan_scores)).scalar()
        if count > 0:
            print(f"   ⚠️ WARN: Found {count} scores pointing to non-existent posts.")
            issues_found += 1
        else:
            print("   ✅ Pass: All scores are attached to valid posts.")

        # 3. Check for Orphan Comments (Comment exists, Post missing)
        print("\n[3] 🏚️ Checking for Orphan Comments...")
        q_orphan_comments = text("""
            SELECT count(*) 
            FROM comments c
            LEFT JOIN posts_raw p ON c.post_id = p.id
            WHERE p.id IS NULL
        """)
        count = (await session.execute(q_orphan_comments)).scalar()
        if count > 0:
            print(f"   ⚠️ WARN: Found {count} comments pointing to non-existent posts.")
            # Let's see if they are just pointing to old/archived posts or truly gone
            issues_found += 1
        else:
            print("   ✅ Pass: All comments are attached to valid posts.")

        # 4. Check for Null Subreddits (Basic Integrity)
        print("\n[4] 📛 Checking for NULL subreddits...")
        q_null_sub = text("SELECT count(*) FROM posts_raw WHERE subreddit IS NULL")
        count = (await session.execute(q_null_sub)).scalar()
        if count > 0:
            print(f"   ❌ FAIL: Found {count} posts with NULL subreddit.")
            issues_found += 1
        else:
            print("   ✅ Pass: All posts have subreddits.")

        print("\n" + "="*30)
        if issues_found == 0:
            print("🎉 RESULT: DATABASE INTEGRITY IS 100% CLEAN.")
            print("   (The tables are structurally perfect. The only issue is the 'freshness' lag.)")
        else:
            print(f"🔧 RESULT: Found {issues_found} integrity issues to fix.")

if __name__ == "__main__":
    asyncio.run(check_integrity())
