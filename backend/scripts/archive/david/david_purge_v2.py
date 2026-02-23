import sys
import os
import asyncio
from sqlalchemy import text
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory

async def execute_robust_purge():
    session = SessionFactory()
    try:
        # The Hit List
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
        
        print(f"--- 🧹 稳健清理模式 (Robust Purge) ---")
        
        # Increase timeout to 5 minutes
        await session.execute(text("SET statement_timeout = '300s'"))
        
        total_moved = 0
        
        for subreddit in kill_list:
            print(f"\nTargeting: {subreddit}")
            try:
                # 1. Count
                count_sql = f"SELECT COUNT(*) FROM posts_raw WHERE subreddit = '{subreddit}'"
                result = await session.execute(text(count_sql))
                count = result.scalar()
                
                if count == 0:
                    print(f"  - Empty. Skipping.")
                    continue
                
                print(f"  - Found {count} posts. Processing...")

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
                
                # 3. Delete Dependencies (Cascade manually)
                print(f"  - ✂️  Cleaning dependencies...")
                
                # Labels
                await session.execute(text(f"DELETE FROM post_semantic_labels WHERE post_id IN (SELECT id FROM posts_raw WHERE subreddit = '{subreddit}')"))
                
                # Embeddings
                await session.execute(text(f"DELETE FROM post_embeddings WHERE post_id IN (SELECT id FROM posts_raw WHERE subreddit = '{subreddit}')"))
                
                # Scores
                await session.execute(text(f"DELETE FROM post_scores WHERE post_id IN (SELECT id FROM posts_raw WHERE subreddit = '{subreddit}')"))
                
                # Comments (This was the bottleneck)
                print(f"  - 🗑  Deleting comments...")
                await session.execute(text(f"DELETE FROM comments WHERE subreddit = '{subreddit}'"))
                
                # 4. Final Delete
                print(f"  - 🔥 Deleting posts...")
                await session.execute(text(f"DELETE FROM posts_raw WHERE subreddit = '{subreddit}'"))
                
                # Commit PER SUBREDDIT
                await session.commit()
                print(f"  - ✅ {subreddit} Cleared.")
                total_moved += count
                
            except Exception as sub_e:
                print(f"  - ❌ Error processing {subreddit}: {sub_e}")
                await session.rollback()
                # Continue to next subreddit? Yes.
        
        print(f"\n✅ JOB DONE. Total posts moved/deleted: {total_moved}")

    except Exception as e:
        print(f"❌ Critical script error: {e}")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(execute_robust_purge())
