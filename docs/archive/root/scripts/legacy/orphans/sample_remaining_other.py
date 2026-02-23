#!/usr/bin/env python3
"""
Sample remaining 'Other' pain content to help diagnose what's left.
Outputs to reports/remaining_other_sample.md for easy reading.
"""
import asyncio
import json
from pathlib import Path
from sqlalchemy import text
from app.db.session import SessionFactory

OUTPUT_PATH = Path("reports/remaining_other_sample.md")

async def sample():
    async with SessionFactory() as session:
        # Sample Comments
        comments = await session.execute(text("""
            SELECT 
                cl.aspect, 
                c.body,
                cp.name as subreddit
            FROM content_labels cl
            JOIN comments c ON cl.content_id = c.id
            JOIN community_pool cp ON LOWER(c.subreddit) = LOWER(cp.name)
            WHERE cl.category = 'pain' 
              AND cl.aspect = 'other'
              AND cp.is_active = true
            ORDER BY RANDOM()
            LIMIT 50
        """))
        
        # Sample Posts
        posts = await session.execute(text("""
            SELECT 
                cl.aspect, 
                p.title,
                p.body,
                cp.name as subreddit
            FROM content_labels cl
            JOIN posts_raw p ON cl.content_id = p.id
            JOIN community_pool cp ON LOWER(p.subreddit) = LOWER(cp.name)
            WHERE cl.category = 'pain' 
              AND cl.aspect = 'other'
              AND cp.is_active = true
            ORDER BY RANDOM()
            LIMIT 20
        """))

    with open(OUTPUT_PATH, "w") as f:
        f.write("# Remaining 'Other' Pain Analysis\n\n")
        f.write("## Posts (Sample 20)\n")
        for row in posts:
            title = (row.title or "").replace("\n", " ")
            body = (row.body or "")[:200].replace("\n", " ") + "..."
            f.write(f"- **[r/{row.subreddit}]**: {title}\n  > {body}\n\n")
            
        f.write("\n---\n\n")
        f.write("## Comments (Sample 50)\n")
        for row in comments:
            body = (row.body or "").replace("\n", " ")
            f.write(f"- **[r/{row.subreddit}]**: {body}\n")

    print(f"✅ Sample written to {OUTPUT_PATH}")

if __name__ == "__main__":
    asyncio.run(sample())
