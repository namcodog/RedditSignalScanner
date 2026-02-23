import asyncio
import os
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load env
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(backend_dir, '.env')
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
if "postgresql+asyncpg" not in DATABASE_URL and "postgresql://" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def backfill_community_ids():
    async with AsyncSessionLocal() as session:
        print("🚀 Starting Backfill of community_id...")
        
        # 1. Load Map (Name -> ID)
        print("   Loading community map...")
        result = await session.execute(text("SELECT id, name FROM community_pool"))
        comm_map = {row.name.lower(): row.id for row in result.fetchall()}
        print(f"   Loaded {len(comm_map)} communities.")

        # 2. Batch Update
        batch_size = 500
        processed = 0
        updated = 0
        
        while True:
            # Fetch unlinked posts
            # Use lower(subreddit) in Python to match map, but query raw string
            rows = await session.execute(text(f"""
                SELECT id, subreddit 
                FROM posts_raw 
                WHERE community_id IS NULL 
                LIMIT {batch_size}
            """))
            posts = rows.fetchall()
            
            if not posts:
                break
                
            updates = []
            for p in posts:
                key = p.subreddit.lower() if p.subreddit else ""
                if key.startswith("r/"):
                    pass # key is good
                elif key:
                    key = "r/" + key # normalization attempt
                    
                if key in comm_map:
                    updates.append({"pid": p.id, "cid": comm_map[key]})
            
            if updates:
                # Bulk update using values list for speed
                # Or use executemany with simple update
                # Construct a CASE statement for a single query (faster than many updates)
                # But executemany is safer for huge sets in asyncpg
                
                # Let's try explicit batch update with executemany
                await session.execute(
                    text("UPDATE posts_raw SET community_id = :cid WHERE id = :pid"),
                    updates
                )
                await session.commit()
                updated += len(updates)
            
            processed += len(posts)
            print(f"   Processed {processed} posts... Updated {updated} links.")
            
            # If we fetched posts but updated none (orphans), we might loop forever if we don't handle them.
            # So we should probably mark them or skip them. 
            # But query selects 'WHERE community_id IS NULL', so if we don't update, we fetch same again.
            # FIX: If we can't find a map, maybe we should skip/log?
            # For now, let's assume coverage is good. If we get stuck, we'll see logs.
            
            if not updates and len(posts) > 0:
                print("⚠️ Found posts with no matching community in pool. Stopping to prevent loop.")
                # Print sample
                for p in posts[:3]:
                    print(f"   - Orphan: {p.subreddit}")
                break

        print(f"✅ Backfill Complete. Total Linked: {updated}")

if __name__ == "__main__":
    asyncio.run(backfill_community_ids())
