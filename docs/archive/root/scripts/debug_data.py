import asyncio
import sys
from pathlib import Path
from sqlalchemy import text
from backend.app.db.session import SessionFactory

# Ensure backend is in pythonpath
sys.path.append(str(Path(__file__).resolve().parent.parent))

async def debug_data():
    async with SessionFactory() as session:
        # 1. Check T1 Communities
        print("--- Checking T1 Communities ---")
        rows = await session.execute(text("SELECT name, tier, is_active FROM community_pool WHERE tier='high'"))
        t1_comms = rows.fetchall()
        print(f"Found {len(t1_comms)} T1 communities.")
        for r in t1_comms[:5]:
            print(f"  - {r.name} (tier={r.tier}, active={r.is_active})")
            
        # 2. Check Posts Raw Sample
        print("\n--- Checking Posts Raw Sample ---")
        rows = await session.execute(text("SELECT subreddit, created_at FROM posts_raw LIMIT 5"))
        posts = rows.fetchall()
        for r in posts:
            print(f"  - Subreddit: '{r.subreddit}', Created: {r.created_at}")
            
        # 3. Check Subreddit Format Match
        if t1_comms:
            sample_t1 = t1_comms[0].name.lower()
            sample_t1_stripped = sample_t1.replace("r/", "")
            print(f"\n--- Testing Match for '{sample_t1}' ---")
            
            # Try exact match
            cnt = await session.execute(text("SELECT COUNT(*) FROM posts_raw WHERE lower(subreddit) = :s"), {"s": sample_t1})
            print(f"  - Match '{sample_t1}': {cnt.scalar_one()}")
            
            # Try stripped match
            cnt = await session.execute(text("SELECT COUNT(*) FROM posts_raw WHERE lower(subreddit) = :s"), {"s": sample_t1_stripped})
            print(f"  - Match '{sample_t1_stripped}': {cnt.scalar_one()}")

        # 4. Check Total Posts in last 12m (ignoring community filter)
        print("\n--- Checking Total Posts (Last 12m, No Filter) ---")
        cnt = await session.execute(text("SELECT COUNT(*) FROM posts_raw WHERE created_at >= NOW() - interval '1 year'"))
        print(f"  - Total Recent Posts: {cnt.scalar_one()}")

if __name__ == "__main__":
    asyncio.run(debug_data())
