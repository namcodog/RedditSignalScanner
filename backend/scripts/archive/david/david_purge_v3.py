import sys
import os
import asyncio
from sqlalchemy import text
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory

async def execute_robust_purge_v3():
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
        
        print(f"--- 🧹 稳健清理模式 V3 (Robust Purge V3) ---")
        
        # Increase general statement timeout to 10 minutes (600s)
        await session.execute(text("SET statement_timeout = '600s'"))
        
        total_moved = 0
        
        for subreddit in kill_list:
            print(f"\nTargeting: {subreddit}")
            try:
                # 1. Count posts
                count_sql = f"SELECT COUNT(*) FROM posts_raw WHERE subreddit = '{subreddit}'"
                result = await session.execute(text(count_sql))
                count = result.scalar()
                
                if count == 0:
                    print(f"  - Empty posts. Skipping {subreddit}.")
                    await session.commit() # Commit even if nothing to do for this sub
                    continue
                
                print(f"  - Found {count} posts to process.")

                # 2. Move (Quarantine)
                print(f"  - 🚚 Moving posts to quarantine...")
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
                
                # 3. Delete Dependencies (Cascade manually)
                print(f"  - ✂️  Cleaning post dependencies...")
                
                # Labels
                await session.execute(text(f"""
                    DELETE FROM post_semantic_labels 
                    WHERE post_id IN (SELECT id FROM posts_raw WHERE subreddit = '{subreddit}')
                """))
                
                # Embeddings
                await session.execute(text(f"""
                    DELETE FROM post_embeddings 
                    WHERE post_id IN (SELECT id FROM posts_raw WHERE subreddit = '{subreddit}')
                """))
                
                # Scores
                await session.execute(text(f"""
                    DELETE FROM post_scores 
                    WHERE post_id IN (SELECT id FROM posts_raw WHERE subreddit = '{subreddit}')
                """))
                
                # Comments (Batch deletion)
                print(f"  - 🗑  Deleting comments in batches for {subreddit}...")
                BATCH_SIZE = 5000
                comments_deleted_for_sub = 0
                while True:
                    # Select IDs to delete in a batch
                    select_batch_sql = f"""
                        SELECT id FROM comments 
                        WHERE subreddit = '{subreddit}' 
                        LIMIT {BATCH_SIZE}
                    """
                    batch_result = await session.execute(text(select_batch_sql))
                    batch_ids = [row[0] for row in batch_result.fetchall()]

                    if not batch_ids:
                        break # No more comments for this subreddit

                    # Delete the batch
                    delete_batch_sql = f"""
                        DELETE FROM comments WHERE id IN ({', '.join(map(str, batch_ids))})
                    """
                    await session.execute(text(delete_batch_sql))
                    comments_deleted_for_sub += len(batch_ids)
                    print(f"    -> Deleted {comments_deleted_for_sub} comments so far for {subreddit}...")
                    
                    # Commit after each comment batch to release locks faster (optional, but safer for large volumes)
                    # await session.commit() 
                    # If committing within batch, the outer commit won't cover post deletions.
                    # Better to let the outer commit handle all dependencies for the subreddit.

                print(f"    -> Total comments deleted for {subreddit}: {comments_deleted_for_sub}")

                # 4. Final Blow: Delete from Raw
                print(f"  - 🔥 Deleting posts from posts_raw for {subreddit}...")
                await session.execute(text(f"DELETE FROM posts_raw WHERE subreddit = '{subreddit}'"))
                
                # Commit all changes for this single subreddit
                await session.commit()
                print(f"  - ✅ {subreddit} Cleanup complete.")
                total_moved += count
                
            except Exception as sub_e:
                print(f"  - ❌ Error processing {subreddit}: {sub_e}")
                await session.rollback() # Rollback changes for THIS subreddit if error
                # Continue to next subreddit
        
        print(f"\n✅ JOB DONE. Total posts moved/deleted from main table: {total_moved}")

    except Exception as e:
        print(f"❌ Critical script error during overall process: {e}")
        # Rollback is not session-wide here due to per-subreddit commits, 
        # but if a global error, ensure session is closed.
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(execute_robust_purge_v3())
