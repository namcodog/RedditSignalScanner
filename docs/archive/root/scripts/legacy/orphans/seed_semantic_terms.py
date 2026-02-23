import asyncio
import yaml
import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import json

# 简单的配置读取
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("DATABASE_URL="):
                    DATABASE_URL = line.strip().split("=", 1)[1]
                    break

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set")

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

LEXICON_PATH = Path("config/semantic_sets/crossborder_v2.1.yml")

async def seed_semantic_terms():
    print(f"📚 Loading lexicon from {LEXICON_PATH}...")
    if not LEXICON_PATH.exists():
        print(f"❌ File not found: {LEXICON_PATH}")
        return

    with open(LEXICON_PATH) as f:
        data = yaml.safe_load(f)

    terms_to_insert = []
    
    # 适配 v2.1 结构: layers -> L1 -> brands -> [...]
    layers = data.get("layers", {})
    
    for layer_name, categories in layers.items():
        # layer_name: L1, L2, L3, L4
        for category_name, items in categories.items():
            # category_name: brands, features, pain_points, etc.
            # Normalize category name to singular (brand, feature, pain_point)
            cat_singular = category_name.rstrip('s')
            if category_name == "pain_points":
                cat_singular = "pain_point"
                
            for item in items:
                # item structure: {canonical, aliases, weight, ...}
                # or simple string (handled just in case)
                if isinstance(item, dict):
                    canonical = item.get("canonical")
                    weight = item.get("weight", 1.0)
                    aliases = item.get("aliases", [])
                    precision = item.get("precision_tag", "high")
                    polarity = item.get("polarity", "neutral")
                else:
                    canonical = str(item)
                    weight = 1.0
                    aliases = []
                    precision = "high"
                    polarity = "neutral"

                terms_to_insert.append({
                    "canonical": canonical,
                    "layer": layer_name,
                    "category": cat_singular,
                    "weight": weight,
                    "aliases": aliases,  # Keep as list, will json.dumps later if needed, or cast for array
                    "precision_tag": precision,
                    "polarity": polarity
                })

    print(f"🚀 Found {len(terms_to_insert)} terms to insert.")
    
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        # 清空旧数据 (可选，为了保证干净)
        # await conn.execute(text("TRUNCATE TABLE semantic_terms RESTART IDENTITY CASCADE;"))
        
        for term in terms_to_insert:
            aliases_list = term["aliases"] if term["aliases"] else []
            await conn.execute(
                text("""
                    INSERT INTO semantic_terms 
                    (canonical, layer, category, weight, lifecycle, created_at, updated_at, aliases, precision_tag, polarity) 
                    VALUES (:canonical, :layer, :category, :weight, 'approved', NOW(), NOW(), CAST(:aliases AS text[]), :precision_tag, :polarity)
                    ON CONFLICT (canonical) DO UPDATE SET
                        layer = EXCLUDED.layer,
                        category = EXCLUDED.category,
                        weight = EXCLUDED.weight,
                        aliases = EXCLUDED.aliases,
                        precision_tag = EXCLUDED.precision_tag,
                        updated_at = NOW()
                """),
                {
                    "canonical": term['canonical'],
                    "layer": term['layer'],
                    "category": term['category'],
                    "weight": term['weight'],
                    "aliases": aliases_list,
                    "precision_tag": term['precision_tag'],
                    "polarity": term['polarity']
                }
            )
    
    print("✅ Seed complete!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_semantic_terms())
