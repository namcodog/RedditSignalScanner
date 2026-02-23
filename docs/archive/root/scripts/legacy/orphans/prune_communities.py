#!/usr/bin/env python3
"""
Deactivate noise communities identified in Phase B14.
"""
import asyncio
from sqlalchemy import text
from app.db.session import SessionFactory

KILL_LIST = [
    # Employee / Rants
    "amazonfc", "fascamazon", "walmartcanada", "amazonemployees", "fuckamazon",
    # Drama / Off-topic
    "relationships", "relationship_advice", "marriage", "divorce", "familyissues",
    # Tier 2: Lifestyle / Philosophy / Memes (Low Product Pains)
    "askwomen", "hydrohomies", "thriftstorehauls", "minimalism", "simpleliving",
    "financialindependence", "leanfire", "personalfinance", "povertyfinance",
    "decidingtobetter", "getdisciplined", "meditation"
]

async def deactivate():
    async with SessionFactory() as session:
        print(f"Deactivating {len(KILL_LIST)} communities...")
        
        # Deactivate
        await session.execute(text("""
            UPDATE community_pool 
            SET is_active = false 
            WHERE LOWER(name) = ANY(:names)
        """), {"names": KILL_LIST})
        
        await session.commit()
        print("✅ Deactivation complete.")

if __name__ == "__main__":
    asyncio.run(deactivate())
