
import asyncio
import sys
import csv
from pathlib import Path
from sqlalchemy import text
from backend.app.db.session import SessionFactory

# Ensure backend is in pythonpath
sys.path.append(str(Path.cwd()))

async def export_dataset():
    output_file = "datasets/ecommerce_core_v0.csv"
    
    print(f"🚀 Starting export for 'Ecommerce_Business' core dataset...")
    
    async with SessionFactory() as session:
        # Complex query to join pools, raw posts, and scores
        # Logic: 
        # 1. Find communities in 'Ecommerce_Business'
        # 2. Find posts in those communities that are 'active' (is_current=true)
        # 3. Filter by Time (last 18 months)
        # 4. Filter by Quality (post_scores.business_pool = 'core')
        # 5. Sort by Engagement (score * num_comments)
        # 6. Limit 3000
        
        query = text("""
            SELECT 
                p.source_post_id as post_id,
                p.subreddit,
                p.title,
                p.body as selftext,
                p.score,
                p.num_comments,
                p.created_at,
                p.url as permalink,
                s.value_score
            FROM posts_raw p
            JOIN community_pool cp ON lower(p.subreddit) = lower(cp.name)
            JOIN post_scores s ON p.id = s.post_id
            WHERE 
                cp.vertical = 'Ecommerce_Business'
                AND p.is_current = true
                AND s.is_latest = true
                AND s.rule_version = 'rulebook_v1'
                AND s.business_pool = 'core'
                AND p.created_at >= NOW() - INTERVAL '18 MONTHS'
            ORDER BY (p.score * p.num_comments) DESC
            LIMIT 3000
        """)
        
        result = await session.execute(query)
        rows = result.fetchall()
        
        if not rows:
            print("⚠️ No data found! Check criteria.")
            return

        print(f"✅ Found {len(rows)} records. Writing to {output_file}...")
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Header
            writer.writerow(['post_id', 'subreddit', 'title', 'selftext', 'score', 'num_comments', 'created_at', 'permalink', 'value_score'])
            
            # Rows
            for r in rows:
                # Clean body text slightly (remove newlines for CSV safety if needed, though csv module handles it)
                # Just limiting length for preview if needed, but for dataset we keep full.
                writer.writerow([
                    r.post_id,
                    r.subreddit,
                    r.title,
                    r.selftext,
                    r.score,
                    r.num_comments,
                    r.created_at,
                    r.permalink,
                    r.value_score
                ])
                
        print(f"🎉 Export complete: {output_file}")

if __name__ == "__main__":
    asyncio.run(export_dataset())
