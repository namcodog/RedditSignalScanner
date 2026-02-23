#!/usr/bin/env python3
"""
Ingest vertical market insights from backend/config/vertical_market_insights.yml
to semantic_rules table.
"""
import asyncio
import yaml
from pathlib import Path
from sqlalchemy import text
from app.db.session import SessionFactory

CONFIG_PATH = Path("backend/config/vertical_market_insights.yml")

async def ingest():
    if not CONFIG_PATH.exists():
        print(f"❌ Config not found: {CONFIG_PATH}")
        return

    with open(CONFIG_PATH, "r") as f:
        data = yaml.safe_load(f)

    domains = data.get("domains", [])
    rules = []
    
    print(f"Found {len(domains)} domains in YAML.")

    # Prepare rules
    for d in domains:
        domain_id = d["id"]
        
        # 1. Ingest Pain Points (New for Phase C)
        pain_groups = d.get("pain_points", [])
        for group in pain_groups:
            # Handle list of strings or single string
            terms_in_group = group if isinstance(group, list) else [group]
            for term in terms_in_group:
                if not term or len(term) < 2: continue
                rules.append({
                    "term": term.lower().strip(),
                    "rule_type": "vertical_pain",
                    "weight": 1.5,
                    "domain": domain_id,
                    "aspect": "quality", # Default fallback, relies on attribute mapping later
                    "source": "vertical_insights"
                })

        # 2. Ingest Scenarios (New for Phase C)
        scenario_groups = d.get("scenarios", [])
        for group in scenario_groups:
            terms_in_group = group if isinstance(group, list) else [group]
            for term in terms_in_group:
                if not term or len(term) < 2: continue
                rules.append({
                    "term": term.lower().strip(),
                    "rule_type": "vertical_scenario", # Distinction
                    "weight": 1.2,
                    "domain": domain_id,
                    "aspect": "content", # Scenarios usually relate to Content/Method
                    "source": "vertical_insights"
                })

        # 3. Specs -> Concept/Feature (Neutral/Positive)
        if "specs" in d and d["specs"]:
            for item in d["specs"]:
                # Item can be a string or a list of synonyms
                terms = item if isinstance(item, list) else [item]
                # Filter out None values
                terms = [t for t in terms if t]
                if not terms: continue
                
                primary = terms[0].lower()
                for t in terms:
                    rules.append({
                        "term": t.lower(),
                        "rule_type": "vertical_spec",
                        "weight": 1.0,
                        "domain": domain_id,
                        "aspect": "function", # Specs usually relate to function/features
                        "source": "vertical_dict"
                    })

        # 4. Scenarios -> Context (Neutral)
        # This section is now redundant with the new "2. Ingest Scenarios" above.
        # Keeping it for now as the instruction only added, not removed.
        if "scenarios" in d and d["scenarios"]:
            for item in d["scenarios"]:
                terms = item if isinstance(item, list) else [item]
                terms = [t for t in terms if t]
                if not terms: continue
                
                for t in terms:
                    rules.append({
                        "term": t.lower(),
                        "rule_type": "vertical_scenario",
                        "weight": 0.5, # Lower weight for context
                        "domain": domain_id,
                        "aspect": "content", # Contextual
                        "source": "vertical_dict"
                    })

        # 3. Pain Points -> Pain (Negative)
        if "pain_points" in d and d["pain_points"]:
            for item in d["pain_points"]:
                terms = item if isinstance(item, list) else [item]
                terms = [t for t in terms if t]
                if not terms: continue
                
                for t in terms:
                    # Heuristic: Most vertical pains are Quality or Function.
                    # Dictionary mapping could be better, but default to 'quality' for now
                    # as it covers physical/result defects.
                    aspect = "quality"
                    if any(x in t.lower() for x in ["slow", "lag", "bug", "crash", "stuck", "connect"]):
                        aspect = "function"
                    
                    rules.append({
                        "term": t.lower(),
                        "rule_type": "vertical_pain",
                        "weight": 2.0, # High weight for explicit pain
                        "domain": domain_id,
                        "aspect": aspect,
                        "source": "vertical_dict"
                    })

        # 4. Slang -> Concept (Context)
        if "slang" in d and d["slang"]:
            for item in d["slang"]:
                term = item["term"].lower()
                # Parse synonyms from term like "UL (Ultralight)"
                # But here we just take the term as is for now, or split.
                # Let's simple ingest the full string if it's short, or split by parens?
                # The user format: "Buy Box", "PL (Private Label)"
                
                # Simple split strategy
                clean_terms = []
                if "(" in term:
                    parts = term.replace(")", "").split("(")
                    clean_terms = [p.strip() for p in parts]
                else:
                    clean_terms = [term]
                
                for t in clean_terms:
                    rules.append({
                        "term": t,
                        "rule_type": "vertical_slang",
                        "weight": 1.2,
                        "domain": domain_id,
                        "aspect": "content",
                        "source": "vertical_dict"
                    })

    print(f"Prepared {len(rules)} rules.")

    # DB Ingestion
    async with SessionFactory() as session:
        # Get concept_id for 'domain_pain' - reusing this for all vertical rules for now
        # to pass FK constraint. Ideally we should have separate concepts, but for speed reuse.
        row = await session.execute(text("SELECT id FROM semantic_concepts WHERE code = 'domain_pain'"))
        cid = row.scalar()
        if not cid:
            print("❌ 'domain_pain' concept not found (should exist from previous step).")
            return

        print(f"Using concept_id={cid} (domain_pain) for FK.")
        
        # Batch insert
        count = 0
        for rule in rules:
            rule_params = rule.copy()
            rule_params['concept_id'] = cid
            rule_params['is_active'] = True
            
            await session.execute(
                text("""
                INSERT INTO semantic_rules (concept_id, term, rule_type, weight, is_active, domain, aspect, source)
                VALUES (:concept_id, :term, :rule_type, :weight, :is_active, :domain, :aspect, :source)
                ON CONFLICT (concept_id, term, rule_type) 
                DO UPDATE SET aspect = EXCLUDED.aspect, domain = EXCLUDED.domain, source = EXCLUDED.source, weight = EXCLUDED.weight
                """),
                rule_params
            )
            count += 1
        
        await session.commit()
    
    print(f"✅ Successfully ingested {count} vertical insights rules.")

if __name__ == "__main__":
    asyncio.run(ingest())
