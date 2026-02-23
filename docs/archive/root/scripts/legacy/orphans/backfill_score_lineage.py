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

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=20, max_overflow=10)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def backfill_lineage():
    async with AsyncSessionLocal() as session:
        print("🚀 Starting Smart Backfill of Score Lineage...")
        
        batch_size = 5000
        processed = 0
        updated_ai = 0
        updated_legacy = 0
        
        while True:
            # Fetch pending rows
            rows = await session.execute(text(f"""
                SELECT id, metadata 
                FROM posts_raw 
                WHERE score_source IS NULL 
                LIMIT {batch_size}
            """ ))
            posts = rows.fetchall()
            
            if not posts:
                break
                
            updates_ai = []
            updates_legacy = []
            
            for p in posts:
                meta = p.metadata if p.metadata else {}
                if meta.get('gemini_scored'):
                    updates_ai.append(p.id)
                else:
                    updates_legacy.append(p.id)
            
            # Execute Batch Updates
            if updates_ai:
                await session.execute(
                    text("UPDATE posts_raw SET score_source='ai_gemini_flash_lite', score_version=2 WHERE id = ANY(:ids)"),
                    {"ids": updates_ai}
                )
                updated_ai += len(updates_ai)

            if updates_legacy:
                await session.execute(
                    text("UPDATE posts_raw SET score_source='rule_v1', score_version=1 WHERE id = ANY(:ids)"),
                    {"ids": updates_legacy}
                )
                updated_legacy += len(updates_legacy)
                
            await session.commit()
            processed += len(posts)
            print(f"   Processed {processed}... (AI: {updated_ai}, Legacy: {updated_legacy})")

        print(f"✅ Lineage Backfill Complete.\n   - Total AI Repaired: {updated_ai}\n   - Total Legacy Labeled: {updated_legacy}")

if __name__ == "__main__":
    asyncio.run(backfill_lineage())
