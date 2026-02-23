import asyncio
import os
import sys
from sqlalchemy import text

# Ensure path
sys.path.append(os.path.join(os.getcwd(), "backend"))
from app.db.session import SessionFactory
from app.core.config import settings

async def test_db_write():
    print(f"Connecting to: {settings.database_url}")
    async with SessionFactory() as session:
        try:
            # Create a dummy author first to satisfy FK
            await session.execute(text("INSERT INTO authors (author_id, author_name) VALUES ('test_bot', 'Test Bot') ON CONFLICT DO NOTHING"))
            
            # Insert dummy post
            await session.execute(text("""
                INSERT INTO posts_raw (source, source_post_id, title, subreddit, author_id, created_at, fetched_at)
                VALUES ('test', 'test_id_123', 'DB Connectivity Test', 'r/test', 'test_bot', NOW(), NOW())
                ON CONFLICT (source, source_post_id, version) DO UPDATE SET title = 'Updated Title'
            """))
            await session.commit()
            print("✅ Write successful.")
        except Exception as e:
            print(f"❌ Write failed: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(test_db_write())
