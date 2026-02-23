import sys
import os
import asyncio
from sqlalchemy import text
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory

async def execute_resumable_purge_v5():
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
        
        print(f"--- 🧹 稳健清理模式 V5 (Spoon Feed) ---")
        await session.execute(text("SET statement_timeout = '600s'"))
        
        for subreddit in kill_list:
            print(f"\nTargeting: {subreddit}")
            
            # 1. Count
            count_sql = f"SELECT COUNT(*) FROM posts_raw WHERE subreddit = '{subreddit}'"
            result = await session.execute(text(count_sql))
            count = result.scalar()
            
            if count == 0:
                print(f"  - Empty. Next.")
                continue
            
            print(f"  - Found {count} posts.")

            # 2. Move (Quarantine)
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
            await session.commit()
            
            # 3. Dependencies
            print(f"  - ✂️  Cleaning metadata...")
            # We assume these are fast enough or already done
            await session.execute(text(f"DELETE FROM post_semantic_labels WHERE post_id IN (SELECT id FROM posts_raw WHERE subreddit = '{subreddit}')"))
            await session.execute(text(f"DELETE FROM post_embeddings WHERE post_id IN (SELECT id FROM posts_raw WHERE subreddit = '{subreddit}')"))
            await session.execute(text(f"DELETE FROM post_scores WHERE post_id IN (SELECT id FROM posts_raw WHERE subreddit = '{subreddit}')"))
            await session.commit()
            
            # 4. Comments (Batch)
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
            
            # 5. Posts (Batch Spoon Feed!)
            print(f"  - 🔥 Deleting posts (Spoon feeding)...")
            POST_BATCH = 100 # Very small batch to avoid timeout/locks
            total_deleted = 0
            while True:
                # Select IDs
                sel_posts = f"SELECT id FROM posts_raw WHERE subreddit = '{subreddit}' LIMIT {POST_BATCH}"
                res = await session.execute(text(sel_posts))
                p_ids = [r[0] for r in res.fetchall()]
                
                if not p_ids:
                    break
                
                # Delete IDs
                del_posts = f"DELETE FROM posts_raw WHERE id IN ({', '.join(map(str, p_ids))})"
                await session.execute(text(del_posts))
                await session.commit() # Commit EVERY 100 posts
                
                total_deleted += len(p_ids)
                if total_deleted % 1000 == 0:
                    print(f"    -> Deleted {total_deleted} posts...")
            
            print(f"  - ✅ {subreddit} FINISHED.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(execute_resumable_purge_v5())
