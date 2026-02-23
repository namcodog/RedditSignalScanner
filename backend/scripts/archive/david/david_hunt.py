import sys
import os
import asyncio
from sqlalchemy import text
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory

async def hunt_noise():
    session = SessionFactory()
    try:
        print("--- 🕵️‍♂️ 噪音猎手 (Noise Hunter) ---")
        
        # Keywords that suggest "Worker/Complaint/Irrelevant" communities
        suspicious_keywords = [
            'driver', 'shopper', 'employee', 'associate', 'worker', 
            'retail', 'server', 'starbucks', 'barista', 
            'tales', 'stories', 'vent', 'offmychest', 'confession',
            'job', 'career', 'interview', 'resig', 'fired',
            'sideproject', 'freelance', 'scam'
        ]
        
        # Build the SQL query dynamically for clarity
        # We search in 'name'
        conditions = " OR ".join([f"name ILIKE '%{kw}%'" for kw in suspicious_keywords])
        sql = f"SELECT name, vertical, categories FROM community_pool WHERE {conditions} ORDER BY name"
        
        result = await session.execute(text(sql))
        rows = result.fetchall()
        
        print(f"Found {len(rows)} potential noise communities based on keywords: {suspicious_keywords}")
        print("-" * 40)
        
        grouped = {}
        for row in rows:
            name, vertical, categories = row
            if vertical not in grouped:
                grouped[vertical] = []
            grouped[vertical].append(name)
            
        for vertical, names in grouped.items():
            print(f"\n[{vertical}] ({len(names)} found):")
            for name in names:
                print(f"  - {name}")

    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(hunt_noise())
