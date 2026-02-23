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

# 🖥️ LM Studio Configuration
# 确保您的 LM Studio Local Server 已开启 (默认端口 1234)
API_BASE = "http://127.0.0.1:1234/v1"
API_KEY = "lm-studio" # Dummy key
MODEL_NAME = "local-model" # LM Studio usually ignores this, or use specific name

DATABASE_URL = os.getenv("DATABASE_URL")
if "postgresql+asyncpg" not in DATABASE_URL and "postgresql://" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Lower concurrency for local inference (GPU can usually handle 1-2 streams well, queueing more is fine)
engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=5)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# 📉 Smaller Batch for Local
# Local inference is slower than Cloud. Large batches might timeout or OOM.
BATCH_SIZE = 3

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
    # Target: The "Rest" (Score 3-7), excluding already scored
    # This is for the "Big Wash"
    query = text("""
        SELECT id, title, left(body, 800) as body_snippet
        FROM posts_raw
        WHERE value_score BETWEEN 3 AND 7
          AND (metadata->>'gemini_scored') IS NULL
        ORDER BY created_at DESC
        LIMIT :limit
    """)
    result = await session.execute(query, {"limit": limit})
    return result.fetchall()

async def call_local_llm(session, posts):
    posts_json = json.dumps([{"id": p.id, "content": f"Title: {p.title}\nBody: {p.body_snippet}"} for p in posts])
    full_prompt = f"Posts to Score:\n{posts_json}"
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SCORING_SYSTEM_PROMPT},
            {"role": "user", "content": full_prompt}
        ],
        "temperature": 0.1
    }

    try:
        # Timeout set to 300s for local processing (safety for batching)
        async with session.post(f"{API_BASE}/chat/completions", json=payload, timeout=300) as response:
            if response.status != 200:
                print(f"❌ Local API Error {response.status}: {await response.text()}")
                return None
            
            result = await response.json()
            raw_text = result['choices'][0]['message']['content']
            
            # Clean up potential markdown blocks if local model chats too much
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            
            return json.loads(raw_text)
            
    except Exception as e:
        print(f"❌ Local Error: {type(e).__name__}: {e}")
        return None

async def update_db(scores):
    if not isinstance(scores, list): return # Handle non-list returns
    
    async with AsyncSessionLocal() as session:
        for item in scores:
            try:
                if 'id' not in item or 'score' not in item: continue

                post_id = item['id']
                raw_score = int(item['score'])
                new_score = max(0, min(10, raw_score))
                reason = item.get('reason', 'Local AI')
                
                new_pool = 'lab'
                if new_score >= 8: new_pool = 'core'
                elif new_score <= 2: new_pool = 'noise'
                
                stmt = text("""
                    UPDATE posts_raw
                    SET value_score = :score,
                        business_pool = :pool,
                        score_source = 'local_qwen3_4b',
                        score_version = 3,
                        metadata = jsonb_set(
                            COALESCE(metadata, '{}'::jsonb), 
                            '{gemini_scored}', 
                            CAST(:details AS jsonb)
                    )
                    WHERE id = :id
                """)
                details = json.dumps({"scored_at": "now", "reason": reason, "model": "local_qwen3_4b", "raw_score": raw_score})
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
                        "src": 'local_qwen3_4b'
                    })

            except Exception as e:
                print(f"⚠️ DB Error ID {item.get('id')}: {e}")
        await session.commit()

async def worker(worker_id):
    print(f"🏠 Local Worker {worker_id} ready.")
    async with aiohttp.ClientSession() as http_session:
        while True:
            try:
                async with AsyncSessionLocal() as db_session:
                    posts = await fetch_pending_posts(db_session)
                
                if not posts:
                    print(f"✅ Worker {worker_id}: No more posts.")
                    break
                
                scores = await call_local_llm(http_session, posts)
                
                if scores:
                    await update_db(scores)
                    print(f"Worker {worker_id}: Processed {len(scores)} items locally.")
                else:
                    await asyncio.sleep(2)
                
            except Exception as e:
                print(f"🔥 Worker {worker_id} Error: {e}")
                await asyncio.sleep(5)

async def main():
    # 2 Workers is safer for local LM Studio queue stability
    tasks = [worker(i) for i in range(2)]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
