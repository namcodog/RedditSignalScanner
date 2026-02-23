import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

# Load Env
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(backend_dir, '.env')
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
if "postgresql+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(DATABASE_URL, echo=False)

async def test_trigger():
    print("🧪 Starting Trigger V3 Verification...")
    
    test_cases = [
        # 1. 阻断测试 (Should NOT be inserted)
        {"id": "test_ghost", "title": "", "body": "Ghost content", "expect": "blocked"},
        {"id": "test_short", "title": "Hi", "body": "Short", "expect": "blocked"},
        {"id": "test_del", "title": "Title", "body": "[deleted]", "expect": "blocked"},
        
        # 2. 评分测试 (Should be inserted with specific score)
        {"id": "test_spam", "title": "Free Money", "body": "http://a.com http://b.com http://c.com promo code", "expect": 0},
        {"id": "test_gold", "title": "Which coffee machine to buy?", "body": "I need a recommendation for a machine under $500", "expect": 7},
        {"id": "test_wts", "title": "[WTS] Selling my GPU", "body": "Price $300", "expect": 6},
        {"id": "test_norm", "title": "Just chatting", "body": "This is a normal length post about nothing specific.", "expect": 3},
    ]

    # Use a separate connection for cleanup to ensure it commits
    async with engine.begin() as conn:
        for case in test_cases:
            await conn.execute(text("DELETE FROM posts_raw WHERE source_post_id = :id"), {"id": case['id']})

    # Test Loop
    for case in test_cases:
        print(f"   👉 Testing: {case['id']} ({case.get('expect')})")
        # Each insert gets its own transaction block so failures don't cascade
        try:
            async with engine.begin() as conn:
                # Removed updated_at
                await conn.execute(text("""
                    INSERT INTO posts_raw (source, source_post_id, title, body, subreddit, created_at)
                    VALUES ('test', :id, :title, :body, 'r/test', now())
                """), {"id": case['id'], "title": case['title'], "body": case['body']})
        except Exception as e:
            # If we expect it to be blocked, this might be okay if it raises an error?
            # Actually RETURN NULL usually just results in 0 rows inserted, not an exception.
            # But if there are other constraints (like NOT NULL on title), it might raise.
            # Our trigger handles empty title by blocking.
            pass

    # Verify Results
    print("\n🔍 Verifying Results in DB...")
    async with engine.connect() as conn:
        for case in test_cases:
            res = await conn.execute(text("SELECT value_score, business_pool FROM posts_raw WHERE source_post_id = :id"), {"id": case['id']})
            row = res.fetchone()
            
            if case['expect'] == "blocked":
                if row:
                    print(f"❌ FAILED: {case['id']} should be BLOCKED but found in DB.")
                else:
                    print(f"✅ PASS: {case['id']} blocked.")
            else:
                if not row:
                    print(f"❌ FAILED: {case['id']} missing from DB. (Trigger might have blocked it wrongly)")
                else:
                    score, pool = row
                    if score == case['expect']:
                        print(f"✅ PASS: {case['id']} Score={score} Pool={pool}")
                    else:
                        print(f"❌ FAILED: {case['id']} Expected Score {case['expect']}, Got {score}")

    # Cleanup
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM posts_raw WHERE source = 'test'"))

if __name__ == "__main__":
    asyncio.run(test_trigger())