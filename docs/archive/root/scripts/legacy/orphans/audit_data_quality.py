import asyncio
import os
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

# Load Env
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(backend_dir, '.env')
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
if "postgresql+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(DATABASE_URL, echo=False)

REPORT_DIR = "reports/local-acceptance"
os.makedirs(REPORT_DIR, exist_ok=True)
REPORT_FILE = os.path.join(REPORT_DIR, "data-clean-audit.json")

async def run_audit():
    print("📊 Starting Data Quality Audit...")
    
    audit_data = {
        "timestamp": datetime.now().isoformat(),
        "pools": {},
        "scores": {},
        "spam_types": {},
        "ai_coverage": 0
    }

    async with engine.connect() as conn:
        # 1. Pool Distribution
        res = await conn.execute(text("SELECT business_pool, COUNT(*) FROM posts_raw GROUP BY 1"))
        for row in res:
            audit_data["pools"][row[0] or "null"] = row[1]

        # 2. Score Distribution
        res = await conn.execute(text("SELECT value_score, COUNT(*) FROM posts_raw GROUP BY 1 ORDER BY 1 DESC"))
        for row in res:
            audit_data["scores"][str(row[0])] = row[1]

        # 3. Spam Categories
        res = await conn.execute(text("SELECT spam_category, COUNT(*) FROM posts_raw WHERE spam_category IS NOT NULL GROUP BY 1"))
        for row in res:
            audit_data["spam_types"][row[0]] = row[1]

        # 4. AI Coverage
        res = await conn.execute(text("SELECT COUNT(*) FROM posts_raw WHERE metadata->>'gemini_scored' IS NOT NULL"))
        audit_data["ai_coverage"] = res.scalar()

    # Save Report
    with open(REPORT_FILE, "w") as f:
        json.dump(audit_data, f, indent=2)
    
    print(f"✅ Audit Report saved to: {REPORT_FILE}")
    print(json.dumps(audit_data, indent=2))

if __name__ == "__main__":
    asyncio.run(run_audit())
