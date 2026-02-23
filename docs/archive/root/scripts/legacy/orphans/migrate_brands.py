import asyncio
import os
import sys
import yaml
from pathlib import Path
from sqlalchemy import text, select
from app.db.session import SessionFactory
from app.models.semantic_term import SemanticTerm

# Add backend to path
sys.path.append(os.getcwd())

async def migrate_brands():
    print("🚀 Starting Brand Injection (Incremental) into SemanticTerms...")
    
    config_dir = Path("backend/config/semantic_sets")
    brand_files = list(config_dir.glob("brands_*.yml"))
    
    if not brand_files:
        print("⚠️ No brand files found.")
        return

    async with SessionFactory() as session:
        total_added = 0
        
        for file_path in brand_files:
            print(f"📂 Processing {file_path.name}...")
            try:
                data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
                category = data.get("category", "Uncategorized")
                brands = data.get("brands", [])
                
                if not brands:
                    continue
                
                # 1. Fetch existing terms to avoid dupes (Global check for canonical uniqueness)
                existing_stmt = select(SemanticTerm.canonical)
                existing_terms = set((await session.execute(existing_stmt)).scalars().all())
                
                new_terms = []
                for brand in brands:
                    kw = str(brand).strip().lower()
                    if not kw or kw in existing_terms:
                        continue
                    
                    new_terms.append(SemanticTerm(
                        canonical=kw,
                        category=category,
                        layer="entity",      # Broad layer
                        precision_tag="brand", # Specific tag
                        weight=1.0,
                        lifecycle="approved",
                        aliases=[str(brand)] # Store original case as alias for display
                    ))
                    existing_terms.add(kw)
                
                if new_terms:
                    session.add_all(new_terms)
                    await session.commit()
                    count = len(new_terms)
                    total_added += count
                    print(f"   ✅ Added {count} new brands to {category}")
                else:
                    print(f"   💤 No new brands to add for {category}")
                    
            except Exception as e:
                print(f"❌ Error processing {file_path.name}: {e}")
                await session.rollback()

        print(f"\n🎉 Migration Complete. Total new brands injected: {total_added}")

if __name__ == "__main__":
    asyncio.run(migrate_brands())
