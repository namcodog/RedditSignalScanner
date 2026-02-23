
import asyncio
from sqlalchemy import text
from app.db.session import SessionFactory

async def check_data():
    async with SessionFactory() as session:
        # 1. Check if r/espresso exists
        print("--- Checking Community Counts ---")
        res = await session.execute(text("""
            SELECT subreddit, count(*) 
            FROM posts_raw 
            WHERE lower(subreddit) IN ('r/espresso', 'r/coffee', 'r/legomarket') 
            GROUP BY subreddit
        """))
        rows = res.fetchall()
        if not rows:
            print("❌ No data found for r/espresso, r/coffee, or r/legomarket!")
        else:
            for r in rows:
                print(f"✅ {r[0]}: {r[1]} posts")

        # 2. Check why r/legomarket matches 'machine'
        print("\n--- Checking r/legomarket content for 'machine' ---")
        res_lego = await session.execute(text("""
            SELECT title 
            FROM posts_raw 
            WHERE lower(subreddit) = 'r/legomarket' 
              AND to_tsvector('english', title || ' ' || body) @@ to_tsquery('english', 'machine')
            LIMIT 5
        """,))
        lego_rows = res_lego.fetchall()
        for r in lego_rows:
            print(f"🧱 Lego Match: {r[0]}")

if __name__ == "__main__":
    asyncio.run(check_data())
