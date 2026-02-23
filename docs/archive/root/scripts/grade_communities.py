
import asyncio
import sys
import math
from pathlib import Path
from sqlalchemy import text
from backend.app.db.session import SessionFactory

# Ensure backend is in pythonpath
sys.path.append(str(Path.cwd()))

async def grade_communities():
    async with SessionFactory() as session:
        # 1. Fetch Performance Data
        print("📊 Fetching community performance data...")
        # Note: We join loosely on subreddit name to ensure we capture all data
        query = text("""
            WITH stats AS (
                SELECT 
                    lower(p.subreddit) as sub_key,
                    COUNT(p.id) as total_posts,
                    COUNT(ps.post_id) FILTER (WHERE ps.business_pool = 'core') as core_posts
                FROM posts_raw p
                LEFT JOIN post_scores ps ON p.id = ps.post_id 
                    AND ps.is_latest = true 
                    AND ps.rule_version = 'rulebook_v1'
                WHERE p.is_current = true
                GROUP BY lower(p.subreddit)
            )
            SELECT 
                cp.name,
                cp.vertical,
                COALESCE(s.total_posts, 0) as total_posts,
                COALESCE(s.core_posts, 0) as core_posts
            FROM community_pool cp
            LEFT JOIN stats s ON lower(cp.name) = s.sub_key
            ORDER BY cp.vertical, COALESCE(s.core_posts, 0) DESC, COALESCE(s.total_posts, 0) DESC
        """)
        
        rows = await session.execute(query)
        data = [dict(row) for row in rows.mappings()]
        
        # 2. Group by Vertical
        verticals = {}
        for row in data:
            v = row['vertical'] or "Unclassified"
            if v not in verticals:
                verticals[v] = []
            verticals[v].append(row)
            
        updates = []
        summary = {"active": 0, "lab": 0, "paused": 0}
        
        print("\n🏆 Grading Results by Vertical:")
        
        # 3. Grade within each Vertical
        for v, communities in verticals.items():
            count = len(communities)
            # Thresholds
            active_idx = math.ceil(count * 0.20) # Top 20%
            # If count is small, ensure at least some actives
            if count > 0 and active_idx == 0: active_idx = 1
            
            paused_idx = count - math.floor(count * 0.30) # Bottom 30% starts here
            
            print(f"\n--- {v} (Total: {count}) ---")
            
            for i, comm in enumerate(communities):
                name = comm['name']
                core = comm['core_posts']
                total = comm['total_posts']
                
                # Logic
                if i < active_idx:
                    status = 'active'
                elif i >= paused_idx:
                    status = 'paused'
                    # Safety Net: Don't pause if it actually has good Core content
                    # Stricter threshold: Must have > 300 core posts to stay in Lab despite being bottom tier
                    if core >= 300: 
                        status = 'lab'
                else:
                    status = 'lab'
                
                # Special Case: If TOTAL posts is 0, it might be new. Set to 'candidate' or 'lab'?
                # User said: "candidate: new discovery...".
                # For now, if 0 posts, let's set to 'candidate' to imply "needs fetching/checking".
                if total == 0:
                    status = 'candidate'
                
                updates.append(f"UPDATE community_pool SET status = '{status}' WHERE name = '{name}';")
                summary[status] = summary.get(status, 0) + 1
                
                # Print "Flagship" vs "Paused" examples
                if status == 'active':
                    print(f"  🌟 ACTIVE: {name:<20} (Core: {core}, Total: {total})")
                elif status == 'paused' and i == paused_idx: # Print first paused
                    print(f"  ... (Lab: {paused_idx - active_idx} communities) ...")
                    print(f"  💤 PAUSED: {name:<20} (Core: {core}, Total: {total})")

        # 4. Generate SQL File
        with open("update_status.sql", "w") as f:
            f.write("BEGIN;\n")
            f.write("\n".join(updates))
            f.write("\nCOMMIT;\n")
            
        print(f"\n✅ Generated {len(updates)} status updates.")
        print("Summary:", json.dumps(summary, indent=2))

if __name__ == "__main__":
    import json
    asyncio.run(grade_communities())
