import asyncio
import os
import sys
from sqlalchemy import select, text

sys.path.append(os.path.join(os.getcwd(), "backend"))
from app.db.session import SessionFactory
from app.models.posts_storage import PostRaw

async def debug_query():
    async with SessionFactory() as session:
        # 1. Test raw SQL query
        print("--- Raw SQL Test ---")
        result = await session.execute(text("SELECT count(*) FROM posts_raw WHERE subreddit='r/baking'"))
        print(f"Raw Count: {result.scalar()}")

        # 2. Test ORM Query (simulating _upsert_to_cold_storage)
        print("--- ORM Query Test ---")
        post_id = "1p84na5"  # Picking a known ID from previous query
        stmt = (
            select(PostRaw)
            .where(
                PostRaw.source == "reddit",
                PostRaw.source_post_id == post_id,
            )
            .order_by(PostRaw.version.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        post = result.scalar_one_or_none()
        print(f"ORM Found: {post}")
        if post:
            print(f"  ID: {post.id}, Ver: {post.version}, Fetched: {post.fetched_at}")

if __name__ == "__main__":
    asyncio.run(debug_query())
