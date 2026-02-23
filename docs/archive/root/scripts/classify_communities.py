
import asyncio
import sys
import json
from pathlib import Path
from sqlalchemy import text
from backend.app.db.session import SessionFactory

# Ensure backend is in pythonpath
sys.path.append(str(Path.cwd()))

VERTICALS = {
    "Ecommerce_Business": ["shopify", "amazon", "ecommerce", "dropship", "fba", "marketing", "business", "entrepreneur", "sales", "seo", "ppc", "advertising", "smallbusiness", "startup", "freelance"],
    "Tools_EDC": ["edc", "knife", "knives", "flashlight", "tool", "gear", "carry", "leatherman", "multitool", "tactical", "watch", "pen"],
    "Minimal_Outdoor": ["camping", "hiking", "ultralight", "onebag", "outdoors", "wilderness", "survival", "bushcraft", "backpacking", "travel"],
    "Family_Parenting": ["parenting", "mom", "dad", "baby", "pregnancy", "kid", "toddler", "daddit", "mommit", "family", "child"],
    "Food_Coffee_Lifestyle": ["coffee", "espresso", "barista", "food", "cooking", "baking", "tea", "kitchen", "recipe", "grilling", "sousvide"],
    "Frugal_Living": ["frugal", "povertyfinance", "buyitforlife", "budget", "saving", "finance", "money", "deal", "coupon", "thrift"],
    "Home_Lifestyle": ["home", "cleaning", "organizing", "interior", "decor", "diy", "gardening", "house", "furniture", "living", "homestead"]
}

async def classify():
    async with SessionFactory() as session:
        # Fetch all active communities
        query = text("SELECT name, categories FROM community_pool WHERE is_active = true ORDER BY name")
        rows = await session.execute(query)
        communities = rows.fetchall()
        
        results = []
        
        for r in communities:
            sub = r.name
            cats = r.categories or []
            suggested = None
            
            # 1. Check existing categories
            for c in cats:
                if c in VERTICALS:
                    suggested = c
                    break
            
            # 2. Keyword match if no existing category
            if not suggested:
                sub_lower = sub.lower()
                for v, keywords in VERTICALS.items():
                    for k in keywords:
                        if k in sub_lower:
                            suggested = v
                            break
                    if suggested:
                        break
            
            results.append({"subreddit": sub, "suggested": suggested})

        # Output for David to review
        print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(classify())
