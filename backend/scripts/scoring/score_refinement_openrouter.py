import os
import sys
import json
import asyncio
import logging
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv

# 1. Load Env
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(backend_dir, '.env')
load_dotenv(env_path)

API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
if not API_KEY:
    print("❌ Error: No OPENROUTER_API_KEY found")
    sys.exit(1)

# Configuration
MODEL_NAME = "openai/gpt-oss-120b"
BATCH_SIZE = 50
CONCURRENCY = 20 # 20 Workers for OpenRouter

# DB Config
DATABASE_URL = os.getenv("DATABASE_URL")
if "postgresql+asyncpg" not in DATABASE_URL and "postgresql://" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Large pool for concurrency
engine = create_async_engine(DATABASE_URL, echo=False, pool_size=40, max_overflow=20)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Client Config
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
    default_headers={
        "HTTP-Referer": "https://reddit-signal-scanner.local", # Required by OpenRouter
        "X-Title": "Reddit Signal Scanner"
    }
)

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
    # Target: Full Wash (Score 3-7)
    # Exclude already scored by THIS model (or any AI if we want fresh start)
    # Checking 'gemini_scored' key exists is a proxy for "AI Scored".
    # Since we are re-washing 3-point posts, we might want to overwrite old 'rule_v1' scores.
    # Query targets any 3-7 score that hasn't been touched by THIS specific upgrade cycle?
    # Or just target anything without AI metadata.
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

async def call_openrouter(posts):
    posts_input = [{"id": p.id, "content": f"Title: {p.title}\nBody: {p.body_snippet}"} for p in posts]
    
    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SCORING_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(posts_input)}
            ],
            response_format={"type": "json_object"},
            timeout=120
        )
        
        content = response.choices[0].message.content
        
        # Robust JSON parsing
        try:
            data = json.loads(content)
            # Handle various return formats (list, dict with 'items', etc.)
            if isinstance(data, list): return data
            if "items" in data: return data["items"]
            if "posts" in data: return data["posts"]
            # Try to find the first list value
            for v in data.values():
                if isinstance(v, list): return v
            return []
        except json.JSONDecodeError:
            print("⚠️ JSON Parse Error")
            return []
            
    except Exception as e:
        print(f"❌ API Error: {e}")
        return None

async def update_db(scores):
    if not scores: return
    
    async with AsyncSessionLocal() as session:
        for item in scores:
            try:
                if 'id' not in item or 'score' not in item: continue

                post_id = item['id']
                raw_score = int(item['score'])
                new_score = max(0, min(10, raw_score))
                reason = item.get('reason', 'AI')
                
                new_pool = 'lab'
                if new_score >= 8: new_pool = 'core'
                elif new_score <= 2: new_pool = 'noise'
                
                # 1. Update Post
                stmt = text("""
                    UPDATE posts_raw
                    SET value_score = :score,
                        business_pool = :pool,
                        score_source = 'ai_gpt_oss_120b',
                        score_version = 3,
                        metadata = jsonb_set(
                            COALESCE(metadata, '{}'::jsonb), 
                            '{gemini_scored}', 
                            CAST(:details AS jsonb)
                    )
                    WHERE id = :id
                """)
                details = json.dumps({"scored_at": "now", "reason": reason, "model": MODEL_NAME, "raw_score": raw_score})
                await session.execute(stmt, {"score": new_score, "pool": new_pool, "details": details, "id": post_id})

                # 2. Audit Promotion
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
                        "src": 'ai_gpt_oss_120b'
                    })

            except Exception as e:
                print(f"⚠️ DB Update Error: {e}")
        await session.commit()

async def worker(worker_id):
    print(f"🚀 Worker {worker_id} started.")
    while True:
        try:
            async with AsyncSessionLocal() as db_session:
                posts = await fetch_pending_posts(db_session)
            
            if not posts:
                print(f"✅ Worker {worker_id}: No more posts.")
                break
            
            scores = await call_openrouter(posts)
            
            if scores:
                await update_db(scores)
                core_count = sum(1 for s in scores if s.get('score', 0) >= 8)
                print(f"Worker {worker_id}: Processed {len(scores)}. Core: {core_count}")
            else:
                await asyncio.sleep(5) # Backoff on error
            
        except Exception as e:
            print(f"🔥 Worker {worker_id} Crash: {e}")
            await asyncio.sleep(5)

async def main():
    print(f"🔥 Starting OpenRouter Wash (Model: {MODEL_NAME})")
    tasks = [worker(i) for i in range(CONCURRENCY)]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
