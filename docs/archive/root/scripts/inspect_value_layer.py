import asyncio
import sys
import os
from pathlib import Path
from sqlalchemy import text
from backend.app.db.session import SessionFactory

# Ensure backend is in pythonpath
sys.path.append(str(Path.cwd()))

async def inspect_value_layer():
    async with SessionFactory() as session:
        print("=== Value Layer Inspection ===")
        
        # 1. Distribution of Business Pool
        print("\n[1] Distribution of Business Pool:")
        query_dist = text("""
            SELECT business_pool, count(*), avg(value_score)::numeric(10,2) as avg_score 
            FROM posts_raw 
            WHERE is_current = true
            GROUP BY business_pool 
            ORDER BY count(*) DESC
        """)
        rows = await session.execute(query_dist)
        for r in rows:
            pool = r.business_pool if r.business_pool else "NULL"
            print(f"  - {pool.ljust(10)}: {r.count} posts (Avg Score: {r.avg_score})")

        # 2. Distribution of Value Score
        print("\n[2] Distribution of Value Score (Top 10):")
        query_score = text("""
            SELECT value_score, count(*) 
            FROM posts_raw 
            WHERE is_current = true
            GROUP BY value_score 
            ORDER BY value_score DESC
        """)
        rows = await session.execute(query_score)
        for r in rows:
            score = str(r.value_score) if r.value_score is not None else "NULL"
            print(f"  - Score {score.ljust(4)}: {r.count}")

        # 3. Check Recent Core/Lab Posts
        print("\n[3] Recent Core Pool Examples (Score >= 8):")
        query_core = text("""
            SELECT subreddit, title, value_score, business_pool 
            FROM posts_raw 
            WHERE business_pool = 'core' AND is_current = true
            ORDER BY created_at DESC LIMIT 3
        """)
        rows = await session.execute(query_core)
        core_posts = rows.fetchall()
        if not core_posts:
            print("  (No Core posts found)")
        for r in core_posts:
            print(f"  [{r.value_score}] {r.subreddit}: {r.title[:60]}...")

        print("\n[4] Recent Lab Pool Examples (Score 3-7):")
        query_lab = text("""
            SELECT subreddit, title, value_score, business_pool, spam_category 
            FROM posts_raw 
            WHERE business_pool = 'lab' AND is_current = true
            ORDER BY created_at DESC LIMIT 3
        """)
        rows = await session.execute(query_lab)
        for r in rows:
            spam = f"(Spam: {r.spam_category})" if r.spam_category else ""
            print(f"  [{r.value_score}] {r.subreddit}: {r.title[:60]}... {spam}")

        print("\n[5] Recent Noise Pool Examples (Score <= 2):")
        query_noise = text("""
            SELECT subreddit, title, value_score, business_pool, spam_category 
            FROM posts_raw 
            WHERE business_pool = 'noise' AND is_current = true
            ORDER BY created_at DESC LIMIT 3
        """)
        rows = await session.execute(query_noise)
        for r in rows:
            spam = f"(Spam: {r.spam_category})" if r.spam_category else ""
            print(f"  [{r.value_score}] {r.subreddit}: {r.title[:60]}... {spam}")

if __name__ == "__main__":
    # Load env vars if needed, but SessionFactory usually handles it or expects env vars
    # We might need to manually load .env if it's not in the shell env
    from dotenv import load_dotenv
    load_dotenv("backend/.env")
    
    asyncio.run(inspect_value_layer())
