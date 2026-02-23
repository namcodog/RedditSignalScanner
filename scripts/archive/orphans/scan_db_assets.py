import asyncio
import os
import json
from collections import Counter
from textwrap import dedent

import asyncpg
from dotenv import load_dotenv

# 加载环境变量
load_dotenv("backend/.env")

DB_DSN = f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:{os.getenv('POSTGRES_PASSWORD', 'postgres')}@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'reddit_signal_scanner')}"

async def scan_assets():
    print(f"🔌 Connecting to database: {DB_DSN} ...")
    try:
        conn = await asyncpg.connect(DB_DSN)
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    print("🔍 Scanning Database Assets...\n")

    # 1. 显性层：基础数据量
    print("--- [Layer 1: Explicit Assets (Volume)] ---")
    row = await conn.fetchrow("SELECT COUNT(*) FROM posts_hot")
    hot_count = row[0]
    row = await conn.fetchrow("SELECT COUNT(*) FROM posts_raw")
    raw_count = row[0]
    print(f"📦 Hot Cache (Real-time): {hot_count} posts")
    print(f"🗄️  Cold Archive (History): {raw_count} posts")

    # 2. 隐性层：语义标签 (JSONB Mining)
    print("\n--- [Layer 2: Implicit Assets (Semantics)] ---")
    print("⛏️  Mining JSONB 'content_labels' field from posts_hot (Sampling top 2000)...")
    
    # 我们只抽样2000条，避免扫全表太慢
    rows = await conn.fetch("""
        SELECT content_labels 
        FROM posts_hot 
        WHERE content_labels IS NOT NULL 
        LIMIT 2000
    """)
    
    pain_counter = Counter()
    intent_counter = Counter()
    
    total_labeled = 0
    for r in rows:
        labels = json.loads(r['content_labels']) if isinstance(r['content_labels'], str) else r['content_labels']
        if not labels: continue
        
        total_labeled += 1
        for label in labels:
            cat = label.get('category')
            aspect = label.get('aspect')
            if cat == 'pain':
                pain_counter[aspect] += 1
            elif cat == 'intent':
                intent_counter[aspect] += 1

    print(f"✅ Found labeled posts in sample: {total_labeled}")
    
    if pain_counter:
        print("\n🔥 Top 5 Detected Pain Points (In Sample):")
        for aspect, count in pain_counter.most_common(5):
            print(f"   - {aspect}: {count} mentions")
    else:
        print("\n⚠️  No 'pain' labels found in sample. (Check if crawler is running or dictionary matches)")

    if intent_counter:
        print("\n🛒 Top 5 Detected Intents (In Sample):")
        for aspect, count in intent_counter.most_common(5):
            print(f"   - {aspect}: {count} mentions")
            
    # 3. 实体层：竞品与品牌
    print("\n--- [Layer 3: Entity Assets (Targets)] ---")
    print("⛏️  Mining JSONB 'entities' field...")
    
    rows = await conn.fetch("""
        SELECT entities 
        FROM posts_hot 
        WHERE entities IS NOT NULL 
        LIMIT 2000
    """)
    
    brand_counter = Counter()
    for r in rows:
        entities = json.loads(r['entities']) if isinstance(r['entities'], str) else r['entities']
        if not entities: continue
        
        for ent in entities:
            if ent.get('type') == 'brand':
                brand_counter[ent.get('name')] += 1

    if brand_counter:
        print("\n🏢 Top 5 Mentioned Brands/Competitors:")
        for brand, count in brand_counter.most_common(5):
            print(f"   - {brand}: {count} mentions")
    else:
        print("\n⚠️  No 'brand' entities found in sample.")

    await conn.close()
    print("\n✨ Scan Complete.")

if __name__ == "__main__":
    asyncio.run(scan_assets())
