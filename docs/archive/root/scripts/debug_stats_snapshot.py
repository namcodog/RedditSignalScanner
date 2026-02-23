
import asyncio
from app.db.session import SessionFactory
from app.services.t1_stats import build_stats_snapshot

async def debug_stats():
    async with SessionFactory() as session:
        print("--- Building Stats Snapshot ---")
        stats = await build_stats_snapshot(session, days=365)
        
        found = False
        for c in stats.community_stats:
            if c.subreddit == "r/espresso":
                print(f"✅ Found r/espresso in stats! Posts: {c.posts}, Comments: {c.comments}")
                found = True
                break
        
        if not found:
            print("❌ r/espresso NOT found in stats.community_stats")
            # Print top 10 found
            print("Top 10 found in stats:")
            for c in stats.community_stats[:10]:
                print(f" - {c.subreddit}")

if __name__ == "__main__":
    asyncio.run(debug_stats())
