import sys
import os
import asyncio
from sqlalchemy import text
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory

async def execute_final_purge_v7():
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
        
        print(f"--- 🧹 终极清理模式 V7 (Final Cleanse) ---")
        await session.execute(text("SET statement_timeout = '600s'"))
        
        # REMOVED: Index creation is now handled by create_index_only.py
        # print(f"🚀 准备加速！正在创建关键索引 (idx_posts_raw_duplicate_of)...")
        # create_index_sql = """
        #     CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_raw_duplicate_of 
        #     ON posts_raw (duplicate_of_id);
        # """
        # await session.execute(text(create_index_sql))
        # await session.commit()
        # print(f"✅ 索引创建完成。")

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
                    source, source_post_id, subreddit, title, body, author_name, created_at, NOW(), 'Labor_Noise/Blacklisted'
                FROM posts_raw
                WHERE subreddit = '{subreddit}'
                ON CONFLICT DO NOTHING;
            """
            await session.execute(text(move_sql))
            await session.commit()
            
            # 3. Dependencies
            print(f"  - ✂️  Cleaning metadata...")
            await session.execute(text(f"DELETE FROM post_semantic_labels WHERE post_id IN (SELECT id FROM posts_raw WHERE subreddit = '{subreddit}')"))
            await session.execute(text(f"DELETE FROM post_embeddings WHERE post_id IN (SELECT id FROM posts_raw WHERE subreddit = '{subreddit}')"))
            await session.execute(text(f"DELETE FROM post_scores WHERE post_id IN (SELECT id FROM posts_raw WHERE subreddit = '{subreddit}')"))
            
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
            
            # 4. CUT TIES (User Approved Strategy)
            print(f"  - ⛓️  Cutting duplicate ties (Setting NULL)...")
            unlink_sql = f"UPDATE posts_raw SET duplicate_of_id = NULL WHERE subreddit = '{subreddit}'"
            await session.execute(text(unlink_sql))
            await session.commit()

            # 5. Delete Posts
            print(f"  - 🔥 Deleting posts...")
            await session.execute(text(f"DELETE FROM posts_raw WHERE subreddit = '{subreddit}'"))
            await session.commit()
            
            print(f"  - ✅ {subreddit} Cleanup complete.")
            total_moved += count

        print(f"\n✅ JOB DONE. Total posts moved/deleted: {total_moved}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(execute_final_purge_v7())