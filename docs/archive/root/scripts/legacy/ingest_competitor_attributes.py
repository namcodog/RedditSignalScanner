#!/usr/bin/env python3
"""
Migrate attributes from competitor_layers.yml to semantic_rules table.
Uses backend/config/attribute_mapping.json to map attributes to Aspects.
"""
import asyncio
import json
import yaml
from pathlib import Path
from sqlalchemy import text
from app.db.session import SessionFactory

async def migrate():
    # 1. Load Mapping
    mapping_path = Path("backend/config/attribute_mapping.json")
    with open(mapping_path) as f:
        mapping = json.load(f)
    
    # 2. Load Competitor Layers
    layers_path = Path("backend/config/entity_dictionary/competitor_layers.yml")
    with open(layers_path) as f:
        data = yaml.safe_load(f)
    
    attributes = data.get("layers", {}).get("attributes", {}).get("aliases", [])
    
    # 3. Prepare Rules
    rules = []
    print(f"Found {len(attributes)} attributes in YAML.")
    
    for attr in attributes:
        attr_lower = str(attr).lower().strip()
        if attr_lower in mapping:
            aspect = mapping[attr_lower]
            rules.append({
                "term": attr_lower,
                "label": "attribute",
                "rule_type": "domain_pain", # Treat as generalized domain pain
                "weight": 1.0,
                "is_active": True,
                "domain": "general", # Generic domain
                "aspect": aspect,
                "source": "competitor_layers"
            })
    
    print(f"Mapped {len(rules)} rules to Aspects.")
    
    print(f"Mapped {len(rules)} rules to Aspects.")
    
    # 4. Insert into DB
    async with SessionFactory() as session:
        # Get concept_id for 'domain_pain'
        row = await session.execute(text("SELECT id FROM semantic_concepts WHERE code = 'domain_pain'"))
        cid = row.scalar()
        if not cid:
            # Fallback if text_classifier relies on this concept existing
            print("Creating 'domain_pain' concept...")
            res = await session.execute(text("""
                INSERT INTO semantic_concepts (code, name, description, domain)
                VALUES ('domain_pain', 'Domain Specific Pain', '垂直领域痛点规则', 'general')
                RETURNING id
            """))
            cid = res.scalar()
        
        print(f"Using concept_id={cid} for rules.")

        for rule in rules:
            rule_params = rule.copy()
            rule_params['concept_id'] = cid
            
            await session.execute(
                text("""
                INSERT INTO semantic_rules (concept_id, term, rule_type, weight, is_active, domain, aspect, source)
                VALUES (:concept_id, :term, :rule_type, :weight, :is_active, :domain, :aspect, :source)
                ON CONFLICT (concept_id, term, rule_type) 
                DO UPDATE SET aspect = EXCLUDED.aspect, domain = EXCLUDED.domain, source = EXCLUDED.source
                """),
                rule_params
            )
        await session.commit()
    
    print("✅ Migration complete.")

if __name__ == "__main__":
    asyncio.run(migrate())
