import sys
import os
import asyncio
from sqlalchemy import text
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory

async def execute_resumable_purge():
    session = SessionFactory()
    try:
        kill_list = [
            'r/instacartshoppers', 
            'r/amazondspdrivers', 
            'r/amazonflexdrivers', 
            'r/walmartemployees', 
            'r/amazonemployees', 
            'r/fascamazon', 
            'r/vent', 
            'r/trueoffmychest', 
            'r/sideproject'
        ]
        
        print(f"--- 🧹 稳健清理模式 V4 (Resumable) ---")
        
        # 5 minutes shell timeout is the limit. 
        # We need to make progress visible and persistent within seconds.
        
        for subreddit in kill_list:
            print(f"\nTargeting: {subreddit}")
            
            # 1. Count posts (Quick check)
            # Use a separate session/transaction for counting to keep it light? No, same session is fine.
            count_sql = f"SELECT COUNT(*) FROM posts_raw WHERE subreddit = '{subreddit}'"
            result = await session.execute(text(count_sql))
            count = result.scalar()
            
            if count == 0:
                print(f"  - Empty posts. Skipping.")
                continue
            
            print(f"  - Found {count} posts.")

            # 2. Move to Quarantine (Commit immediately)
            print(f"  - 🚚 Moving to quarantine...")
            move_sql = f"""
                INSERT INTO posts_quarantine (
                    source, source_post_id, subreddit, title, body, author_name, created_at, rejected_at, reject_reason
                )
                SELECT 
                    source, source_post_id, subreddit, title, body, author_name, created_at, NOW(), 'Labor_Noise/Blacklisted'
                FROM posts_raw
                WHERE subreddit = '{subreddit}'
                ON CONFLICT DO NOTHING;
            """
            await session.execute(text(move_sql))
            await session.commit() # <--- SAVEPOINT 1
            
            # 3. Delete Dependencies (Labels/Embeddings/Scores)
            print(f"  - ✂️  Cleaning metadata...")
            # We can do these in one go usually, they are small compared to comments
            await session.execute(text(f"DELETE FROM post_semantic_labels WHERE post_id IN (SELECT id FROM posts_raw WHERE subreddit = '{subreddit}')"))
            await session.execute(text(f"DELETE FROM post_embeddings WHERE post_id IN (SELECT id FROM posts_raw WHERE subreddit = '{subreddit}')"))
            await session.execute(text(f"DELETE FROM post_scores WHERE post_id IN (SELECT id FROM posts_raw WHERE subreddit = '{subreddit}')"))
            await session.commit() # <--- SAVEPOINT 2
            
            # 4. Delete Comments (Batch & Commit)
            print(f"  - 🗑  Deleting comments (Persistent)...")
            BATCH_SIZE = 5000
            total_comments = 0
            while True:
                # Get batch IDs
                select_batch = f"SELECT id FROM comments WHERE subreddit = '{subreddit}' LIMIT {BATCH_SIZE}"
                batch_res = await session.execute(text(select_batch))
                batch_ids = [r[0] for r in batch_res.fetchall()]
                
                if not batch_ids:
                    break
                
                # Delete batch
                del_sql = f"DELETE FROM comments WHERE id IN ({', '.join(map(str, batch_ids))})"
                await session.execute(text(del_sql))
                await session.commit() # <--- SAVEPOINT 3 (Per Batch!)
                
                total_comments += len(batch_ids)
                print(f"    -> Deleted {total_comments} comments...")
            
            # 5. Delete Posts
            print(f"  - 🔥 Deleting posts...")
            await session.execute(text(f"DELETE FROM posts_raw WHERE subreddit = '{subreddit}'"))
            await session.commit() # <--- SAVEPOINT 4 (Final)
            print(f"  - ✅ {subreddit} Done.")

    except Exception as e:
        print(f"❌ Error: {e}")
        # No rollback needed effectively, as we want to keep progress
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(execute_resumable_purge())
