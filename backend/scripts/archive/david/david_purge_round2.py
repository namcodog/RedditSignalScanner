import sys
import os
import asyncio
from sqlalchemy import text
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory

async def execute_purge_round2():
    session = SessionFactory()
    try:
        # Round 2 Kill List
        kill_list = [
            'r/amazonfc', 
            'r/fuckamazon', 
            'r/amazonwtf', 
            'r/amazonfresh', 
            'r/bestaliexpressfinds'
        ]
        
        print(f"--- 🧹 终极清理 Round 2 (The 5 New Targets) ---")
        await session.execute(text("SET statement_timeout = '600s'"))
        
        # Index check (Just a log, we know it exists)
        print(f"ℹ️  Index 'idx_posts_raw_duplicate_of' assumed active for speed.")

        total_moved = 0
        
        for subreddit in kill_list:
            print(f"\nTargeting: {subreddit}")
            
            # 1. Count
            count_sql = f"SELECT COUNT(*) FROM posts_raw WHERE subreddit = '{subreddit}'"
            result = await session.execute(text(count_sql))
            count = result.scalar()
            
            if count == 0:
                print(f"  - Empty. Skipping.")
                continue
            
            print(f"  - Found {count} posts.")

            # 2. Move (Quarantine)
            print(f"  - 🚚 Moving to quarantine...")
            move_sql = f"""
                INSERT INTO posts_quarantine (
                    source, source_post_id, subreddit, title, body, author_name, created_at, rejected_at, reject_reason
                )
                SELECT 
                    source, source_post_id, subreddit, title, body, author_name, created_at, NOW(), 'Labor_Noise/Blacklisted_R2'
                FROM posts_raw
                WHERE subreddit = '{subreddit}'
                ON CONFLICT DO NOTHING;
            """
            await session.execute(text(move_sql))
            await session.commit()
            
            # 3. Dependencies
            print(f"  - ✂️  Cleaning metadata...")
            await session.execute(text(f"DELETE FROM post_semantic_labels WHERE post_id IN (SELECT id FROM posts_raw WHERE subreddit = '{subreddit}')"))
            await session.commit()
            await session.execute(text(f"DELETE FROM post_embeddings WHERE post_id IN (SELECT id FROM posts_raw WHERE subreddit = '{subreddit}')"))
            await session.commit()
            await session.execute(text(f"DELETE FROM post_scores WHERE post_id IN (SELECT id FROM posts_raw WHERE subreddit = '{subreddit}')"))
            await session.commit()
            
            # Comments (Batch)
            print(f"  - 🗑  Deleting comments (Persistent)...")
            BATCH_SIZE = 5000
            while True:
                select_batch = f"SELECT id FROM comments WHERE subreddit = '{subreddit}' LIMIT {BATCH_SIZE}"
                batch_res = await session.execute(text(select_batch))
                batch_ids = [r[0] for r in batch_res.fetchall()]
                if not batch_ids:
                    break
                del_sql = f"DELETE FROM comments WHERE id IN ({', '.join(map(str, batch_ids))})"
                await session.execute(text(del_sql))
                await session.commit()
            
            # 4. CUT TIES (Both Directions)
            print(f"  - ⛓️  Cutting OUTGOING ties...")
            await session.execute(text(f"UPDATE posts_raw SET duplicate_of_id = NULL WHERE subreddit = '{subreddit}'"))
            await session.commit()

            print(f"  - ⛓️  Cutting INCOMING ties...")
            incoming_sql = f"""
                UPDATE posts_raw 
                SET duplicate_of_id = NULL 
                WHERE duplicate_of_id IN (SELECT id FROM posts_raw WHERE subreddit = '{subreddit}')
            """
            await session.execute(text(incoming_sql))
            await session.commit()

            # 5. Delete Posts
            print(f"  - 🔥 Deleting posts...")
            await session.execute(text(f"DELETE FROM posts_raw WHERE subreddit = '{subreddit}'"))
            await session.commit()
            
            print(f"  - ✅ {subreddit} Cleanup complete.")
            total_moved += count

        print(f"\n✅ ROUND 2 DONE. Total posts moved/deleted: {total_moved}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(execute_purge_round2())
