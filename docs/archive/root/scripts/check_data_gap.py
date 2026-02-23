
import asyncio
import sys
from pathlib import Path
from sqlalchemy import text
from backend.app.db.session import SessionFactory

# Ensure backend is in pythonpath
sys.path.append(str(Path.cwd()))

async def check_data_gap():
    async with SessionFactory() as session:
        print("=== 🕵️‍♂️ David's Inspection: The 'New Data' Gap ===")
        
        # 1. Check volume of 'fresh' raw posts (last 24 hours)
        query_fresh_posts = text("""
            SELECT count(*) 
            FROM posts_raw 
            WHERE created_at > NOW() - INTERVAL '24 HOURS'
        """)
        fresh_count = await session.execute(query_fresh_posts)
        fresh_count = fresh_count.scalar()
        print(f"\n[1] Fresh Posts (Last 24h) in 'posts_raw': {fresh_count}")

        if fresh_count == 0:
            print("   ⚠️ No fresh posts? Is the crawler (System A) running?")
        else:
            # 2. Check how many of these have a score in 'post_scores'
            query_scored_fresh = text("""
                SELECT count(DISTINCT p.id)
                FROM posts_raw p
                JOIN post_scores s ON p.id = s.post_id
                WHERE p.created_at > NOW() - INTERVAL '24 HOURS'
            """)
            scored_count = await session.execute(query_scored_fresh)
            scored_count = scored_count.scalar()
            
            print(f"[2] Scored Posts (Last 24h) in 'post_scores': {scored_count}")
            
            gap = fresh_count - scored_count
            print(f"\\n👉 THE GAP: {gap} posts are sitting in the warehouse without a price tag.")
            if gap > 0:
                print("   (System A is bringing them in, but the Scoring Engine isn't checking them.)")

        # 2.5 Check available rule versions
        print("\\n[2.5] Debugging Rule Versions:")
        query_versions = text("SELECT DISTINCT rule_version FROM post_scores")
        rows = await session.execute(query_versions)
        for r in rows:
            print(f"   - Found version: '{r.rule_version}'")

        # 3. Check 'comments' linkage for high value posts (The 'System B' Gap)
        print("\\n[3] Comment Mining Efficiency (High Value Posts):")
        # Find high value posts (score >= 6) from older data to see if they have comments
        query_high_value_coverage = text("""
            SELECT 
                count(DISTINCT p.id) as high_value_posts,
                count(DISTINCT c.post_id) as posts_with_comments
            FROM post_scores s
            JOIN posts_raw p ON s.post_id = p.id
            LEFT JOIN comments c ON p.id = c.post_id
            WHERE s.value_score >= 6
            AND s.rule_version = 'rulebook_v1'
            AND s.is_latest = true
        """)
        
        rows = await session.execute(query_high_value_coverage)
        for r in rows:
            print(f"   - High Value Posts (Score >= 6): {r.high_value_posts}")
            print(f"   - Of those, how many have comments: {r.posts_with_comments}")
            if r.high_value_posts > 0:
                coverage = (r.posts_with_comments / r.high_value_posts) * 100
                print(f"   - Coverage: {coverage:.1f}%")

if __name__ == "__main__":
    asyncio.run(check_data_gap())
