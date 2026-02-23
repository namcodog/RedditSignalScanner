#!/usr/bin/env python3
"""
Deep dive analysis of Vertical Pains.
Counts the frequency of specific vertical pain points within the 'PAIN' category.
"""
import asyncio
import yaml
from collections import defaultdict
from sqlalchemy import text
from app.db.session import SessionFactory

VERTICAL_YAML = "backend/config/vertical_market_insights.yml"

async def analyze():
    # 1. Load Vertical Config
    with open(VERTICAL_YAML) as f:
        data = yaml.safe_load(f)
    
    domains = data.get("domains", [])
    if not domains:
        print("❌ 'domains' key not found in YAML!")
        print(f"YAML Keys: {data.keys()}")
        return

    # 2. Prepare Counters
    stats = defaultdict(lambda: defaultdict(int))
    
    async with SessionFactory() as session:
        print(f"Found {len(domains)} domains.")
        
        for domain in domains:
            v_name = domain.get("name", "Unknown")
            print(f"Scanning domain: {v_name}...")
            
            # Get pain points list
            pain_groups = domain.get("pain_points", [])
            print(f"  > Found {len(pain_groups)} pain groups/terms.")
            # Flatten list of lists/strings
            terms = []
            for group in pain_groups:
                if isinstance(group, list):
                    terms.extend(group)
                else:
                    terms.append(group)
            
            # Query for each term (Inefficient but accurate for analysis)
            # Optimize: Batch query or regex? 
            # Given dataset size (~200k), individual queries might be slow.
            # Better: Fetch all PAIN comments for relevant subreddits (if strictly separated)
            # OR just query ILIKE for each term globally (since we want to see presence).
            
            for term in terms:
                # Basic normalization
                t = term.lower().strip()
                if len(t) < 3: continue
                
                # Check frequency in PAIN comments
                # Note: This scans ALL pain comments. 
                # Ideally we should limit to 'relevant communities' for this vertical, 
                # but cross-vertical pains (e.g. 'rust') might appear elsewhere.
                # Let's count globally to show 'Prevalence'.
                
                # Using a COUNT query
                res = await session.execute(text("""
                    SELECT COUNT(*) 
                    FROM comments c 
                    JOIN content_labels cl ON c.id = cl.content_id 
                    WHERE cl.category = 'pain' 
                    AND c.body ILIKE :pat
                """), {"pat": f"%{t}%"})
                
                count = res.scalar()
                if count > 0:
                    stats[v_name][t] = count
    
    # 3. Output Report
    with open("reports/vertical_pain_breakdown.md", "w") as f:
        f.write("# Vertical Pain Breakdown\n\n")
        f.write("Breakdown of specific vertical pain points found within the 'Category: Pain' dataset.\n\n")
        
        for v_name, counts in stats.items():
            f.write(f"## {v_name}\n")
            if not counts:
                f.write("*No data found*\n")
                continue
                
            sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
            f.write("| Pain Term | Frequency | Implied Aspect |\n")
            f.write("|---|---|---|\n")
            for term, count in sorted_counts[:20]: # Top 20 per vertical
                f.write(f"| {term} | {count} | (See Mapping) |\n")
            f.write("\n")
            
    print("✅ Analysis complete. See reports/vertical_pain_breakdown.md")

if __name__ == "__main__":
    asyncio.run(analyze())
