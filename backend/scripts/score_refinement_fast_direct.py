import os
import sys
import json
import asyncio
import aiohttp
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv

# 1. Load Env
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(backend_dir, '.env')
load_dotenv(env_path)

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("❌ Error: GEMINI_API_KEY not found")
    sys.exit(1)

MODEL_NAME = "gemini-2.5-flash-lite"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

DATABASE_URL = os.getenv("DATABASE_URL")
if "postgresql+asyncpg" not in DATABASE_URL and "postgresql://" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Increase pool size for concurrency
engine = create_async_engine(DATABASE_URL, echo=False, pool_size=40, max_overflow=10)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

BATCH_SIZE = 50

SCORING_SYSTEM_PROMPT = """
You are a Data Value Assessor. Score Reddit posts (0-10) for "Commercial Value".

**Scoring Logic (The 3 Chips):**
Base: 3.
+ Chip 1 (Object): Brand/Product? -> +2
+ Chip 2 (Action): Buy/Sell/Compare? -> +2
+ Chip 3 (Money): Price/Budget? -> +2

**Output:** Return ONLY a valid JSON array. Each item: {"id": int, "score": int, "reason": string}
"""

async def fetch_pending_posts(session, limit=BATCH_SIZE):
    query = text("""
        SELECT id, title, left(body, 800) as body_snippet
        FROM posts_raw
        WHERE value_score BETWEEN 5 AND 7
          AND (metadata->>'gemini_scored') IS NULL
        ORDER BY created_at DESC
        LIMIT :limit
    """)
    result = await session.execute(query, {"limit": limit})
    return result.fetchall()

async def call_google_api(session, posts):
    posts_json = json.dumps([{"id": p.id, "content": f"Title: {p.title}\nBody: {p.body_snippet}"} for p in posts])
    full_prompt = f"{SCORING_SYSTEM_PROMPT}\n\nPosts to Score:\n{posts_json}"
    
    payload = {
        "contents": [{
            "parts": [{"text": full_prompt}]
        }],
        "generationConfig": {
            "response_mime_type": "application/json"
        }
    }

    try:
        async with session.post(API_URL, json=payload) as response:
            if response.status != 200:
                text = await response.text()
                if response.status == 429:
                    print("⚠️ Quota Exceeded (429). Sleeping 5s...")
                    await asyncio.sleep(5)
                    return None
                print(f"❌ API Error {response.status}: {text}")
                return None
            
            result = await response.json()
            try:
                raw_text = result['candidates'][0]['content']['parts'][0]['text']
                return json.loads(raw_text)
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                print(f"⚠️ Parse Error: {e}")
                return None
    except Exception as e:
        print(f"❌ Network Error: {e}")
        return None

async def update_db(scores):
    if not scores: return
    
    async with AsyncSessionLocal() as session:
        for item in scores:
            try:
                if 'id' not in item or 'score' not in item: continue

                post_id = item['id']
                raw_score = int(item['score'])
                
                # 🛡️ 强制钳位 (Clamp) 0-10
                new_score = max(0, min(10, raw_score))
                
                reason = item.get('reason', 'AI')
                
                new_pool = 'lab'
                if new_score >= 8: new_pool = 'core'
                elif new_score <= 2: new_pool = 'noise'
                
                stmt = text("""
                    UPDATE posts_raw
                    SET value_score = :score,
                        business_pool = :pool,
                        score_source = 'ai_gemini_flash_lite',
                        score_version = 2,
                        metadata = jsonb_set(
                            COALESCE(metadata, '{}'::jsonb), 
                            '{gemini_scored}', 
                            CAST(:details AS jsonb)
                    )
                    WHERE id = :id
                """)
                details = json.dumps({"scored_at": "now", "reason": reason, "model": MODEL_NAME, "raw_score": raw_score})
                await session.execute(stmt, {"score": new_score, "pool": new_pool, "details": details, "id": post_id})

                # 📝 Audit Log: Record Promotion
                if new_score >= 8:
                    audit_stmt = text("""
                        INSERT INTO data_audit_events 
                        (event_type, target_type, target_id, reason, new_value, source_component)
                        VALUES ('promote_core', 'post', :id, :reason, :val, :src)
                    """)
                    await session.execute(audit_stmt, {
                        "id": str(post_id),
                        "reason": reason,
                        "val": json.dumps({"score": new_score, "pool": "core"}),
                        "src": 'ai_gemini_flash_lite'
                    })
            except Exception as e:
                print(f"⚠️ DB Update Error ID {item.get('id')}: {e}")
        await session.commit()

async def worker(worker_id):
    print(f"🚀 Worker {worker_id} started.")
    async with aiohttp.ClientSession() as http_session:
        while True:
            try:
                async with AsyncSessionLocal() as db_session:
                    posts = await fetch_pending_posts(db_session)
                
                if not posts:
                    print(f"✅ Worker {worker_id}: No more posts.")
                    break
                
                scores = await call_google_api(http_session, posts)
                
                if scores:
                    await update_db(scores)
                    # 统计
                    core_count = sum(1 for s in scores if min(10, s.get('score', 0)) >= 8)
                    print(f"Worker {worker_id}: Processed {len(scores)} items. Core found: {core_count}")
                else:
                    await asyncio.sleep(2)
                
                # 极速模式：几乎不休眠
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"🔥 Worker {worker_id} Error: {e}")
                await asyncio.sleep(5)

async def main():
    # T1 Tier Scale: 30 concurrent workers (Safe for max_connections=100)
    tasks = [worker(i) for i in range(30)]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
