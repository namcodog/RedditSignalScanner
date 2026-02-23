"""迁移领域痛点配置 to DB
用法: python -m backend.scripts.migrate_domain_pains
"""
import asyncio
import yaml
from pathlib import Path
from sqlalchemy import text
from app.db.session import SessionFactory

CONFIG_PATH = Path(__file__).parent.parent / "config" / "domain_pain_points.yml"

async def migrate():
    if not CONFIG_PATH.exists():
        print(f"❌ Config not found: {CONFIG_PATH}")
        return

    with open(CONFIG_PATH, "r") as f:
        data = yaml.safe_load(f)

    domains = data.get("domains", {})
    total_rules = 0

    async with SessionFactory() as session:
        # 1. Ensure 'domain_pain' concept exists
        row = await session.execute(text("SELECT id FROM semantic_concepts WHERE code = 'domain_pain'"))
        cid = row.scalar()
        if not cid:
            print("Creating 'domain_pain' concept...")
            res = await session.execute(text("""
                INSERT INTO semantic_concepts (code, name, description, domain)
                VALUES ('domain_pain', 'Domain Specific Pain', '垂直领域痛点规则', 'general')
                RETURNING id
            """))
            cid = res.scalar()
        else:
            print(f"Using existing 'domain_pain' concept id={cid}")

        # 2. Iterate domains
        for domain_key, domain_data in domains.items():
            pain_groups = domain_data.get("pain_keywords", {})
            
            for aspect, keywords in pain_groups.items():
                for kw in keywords:
                    # Insert rule
                    # rule_type='domain_pain', meta={'domain': domain_key, 'aspect': aspect}
                    # columns: domain, aspect, source
                    await session.execute(text("""
                        INSERT INTO semantic_rules 
                        (concept_id, term, rule_type, weight, is_active, domain, aspect, source)
                        VALUES (:cid, :term, 'domain_pain', 1.0, true, :domain, :aspect, 'yaml')
                        ON CONFLICT (concept_id, term, rule_type) DO UPDATE SET
                            domain = EXCLUDED.domain,
                            aspect = EXCLUDED.aspect,
                            updated_at = NOW()
                    """), {
                        "cid": cid,
                        "term": kw.lower(),
                        "domain": domain_key,
                        "aspect": aspect
                    })
                    total_rules += 1
        
        await session.commit()
    
    print(f"✅ Migrated {total_rules} domain pain rules.")

if __name__ == "__main__":
    asyncio.run(migrate())
