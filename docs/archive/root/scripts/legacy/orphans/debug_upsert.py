import asyncio
import os
import sys
from sqlalchemy import text

sys.path.append(os.path.join(os.getcwd(), "backend"))
from app.db.session import SessionFactory

async def test_manual_upsert():
    async with SessionFactory() as session:
        try:
            # Use raw SQL to bypass ORM logic and test ON CONFLICT behavior directly
            stmt = text("""
                INSERT INTO posts_raw (
                    source, source_post_id, version, 
                    title, subreddit, author_id, 
                    created_at, fetched_at, is_current, valid_from, valid_to
                )
                VALUES (
                    'reddit', 'test_upsert_1', 1, 
                    'Test Upsert Title', 'r/test', 'test_bot', 
                    NOW(), NOW(), true, NOW(), '9999-12-31 00:00:00'
                )
                ON CONFLICT (source, source_post_id, version) 
                DO UPDATE SET 
                    fetched_at = EXCLUDED.fetched_at,
                    title = 'Updated Title'
                RETURNING xmax = 0 AS inserted;
            """)
            result = await session.execute(stmt)
            row = result.mappings().first()
            print(f"Result: {row}")
            await session.commit()
        except Exception as e:
            print(f"Error: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(test_manual_upsert())
