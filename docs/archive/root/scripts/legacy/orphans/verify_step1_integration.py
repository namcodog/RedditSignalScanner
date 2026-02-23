import asyncio
import json
import os
import sys
from pathlib import Path
from sqlalchemy import text
from app.db.session import SessionFactory
from app.services.t1_stats import build_stats_snapshot

# Add backend to path
sys.path.append(os.getcwd())
from scripts.generate_t1_market_report import _build_facts

async def verify_step1():
    print("🚀 Starting Step 1 Integration Verification...")
    
    async with SessionFactory() as session:
        # 1. Clean Setup
        await session.execute(text("TRUNCATE TABLE posts_raw, post_semantic_labels RESTART IDENTITY CASCADE"))
        
        # 2. Seed Data (Real DB Injection)
        # Amazon (Platform), DeLonghi (Brand), YouTube (Channel)
        await session.execute(text("""
            INSERT INTO authors (author_id, author_name) VALUES ('tester', 'Tester')
        """))
        await session.execute(text("""
            INSERT INTO posts_raw (subreddit, title, body, author_id, is_current, created_at) VALUES
            ('r/coffee', 'Bought from Amazon', 'Amazon delivery was fast', 'tester', true, NOW()),
            ('r/coffee', 'Amazon again', 'I love Amazon', 'tester', true, NOW()),
            ('r/coffee', 'DeLonghi review', 'DeLonghi makes good espresso', 'tester', true, NOW()),
            ('r/coffee', 'Watch YouTube', 'Check this video on YouTube', 'tester', true, NOW())
        """))
        # Semantic labels (required for stats)
        await session.execute(text("""
            INSERT INTO post_semantic_labels (post_id, l1_category) 
            SELECT id, 'Survival' FROM posts_raw
        """))
        
        # Fake entity extraction (simulate NER)
        # In real flow, this comes from content_entities table or _backfill_brand_mentions
        # Here we simulate the input to _build_facts via stats object
        # But wait, _build_facts reads from stats.brand_pain_cooccurrence which comes from DB
        # So we need to seed content_entities too? 
        # No, let's just mock the stats object for the NER part, but rely on the classification logic
        
        await session.commit()
        
        # 3. Run Stats Builder (to get the base object)
        stats = await build_stats_snapshot(session, days=30)
        
        # Manually inject "dirty" entities into stats (simulating raw NER output)
        stats.brand_pain_cooccurrence = [
            {"brand": "Amazon", "mentions": 2, "aspects": []},
            {"brand": "DeLonghi", "mentions": 1, "aspects": []},
            {"brand": "YouTube", "mentions": 1, "aspects": []}
        ]
        
        # 4. Run _build_facts (The Target)
        print("⚙️ Running _build_facts...")
        facts_json = _build_facts(
            stats=stats,
            clusters=[],
            topic="Coffee",
            topic_tokens=set(),
            days=30,
            # We can test backfill logic too if we want
            brand_backfill=[] 
        )
        
        facts = json.loads(facts_json)
        landscape = facts["market_landscape"]
        
        # 5. Assertions
        print(f"📊 Landscape Output: {json.dumps(landscape, indent=2)}")
        
        platforms = [p["name"] for p in landscape["platforms"]]
        brands = [b["name"] for b in landscape["brands"]]
        channels = [c["name"] for c in landscape["channels"]]
        
        if "Amazon" in platforms and "Amazon" not in brands:
            print("✅ SUCCESS: Amazon correctly classified as Platform.")
        else:
            print("❌ FAILURE: Amazon classification wrong.")
            
        if "DeLonghi" in brands:
            print("✅ SUCCESS: DeLonghi correctly classified as Brand.")
        else:
            print("❌ FAILURE: DeLonghi missing from Brands.")
            
        if "YouTube" in channels:
            print("✅ SUCCESS: YouTube correctly classified as Channel.")
        else:
            print("❌ FAILURE: YouTube missing from Channels.")

if __name__ == "__main__":
    # Force test DB env var just in case
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner_test"
    asyncio.run(verify_step1())
