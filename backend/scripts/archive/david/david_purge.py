import sys
import os
import asyncio
from sqlalchemy import text
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory

async def execute_purge():
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
        formatted_list = "', '".join(kill_list)
        
        print(f"--- 🧹 强力大扫除 (Deep Purge) ---")
        
        # 1. Count
        count_sql = f"SELECT COUNT(*) FROM posts_raw WHERE subreddit IN ('{formatted_list}')"
        result = await session.execute(text(count_sql))
        count = result.scalar()
        print(f"🎯 Target Posts to Move & Delete: {count}")
        
        if count == 0:
            print("Nothing to purge.")
            return

        # 2. Move to Quarantine (Copy first)
        print("🚚 Moving data to quarantine...")
        move_sql = f"""
            INSERT INTO posts_quarantine (
                source, source_post_id, subreddit, title, body, author_name, created_at, rejected_at, reject_reason
            )
            SELECT 
                source, source_post_id, subreddit, title, body, author_name, created_at, NOW(), 'Labor_Noise/Blacklisted'
            FROM posts_raw
            WHERE subreddit IN ('{formatted_list}')
            ON CONFLICT DO NOTHING;
        """
        await session.execute(text(move_sql))
        
        # 3. Delete Dependencies (The Roots)
        print("✂️  Cutting roots (Deleting dependencies)...")
        
        # Dependency 1: Semantic Labels
        print("   - Cleaning post_semantic_labels...")
        await session.execute(text(f"""
            DELETE FROM post_semantic_labels 
            WHERE post_id IN (SELECT id FROM posts_raw WHERE subreddit IN ('{formatted_list}'))
        """))
        
        # Dependency 2: Embeddings
        print("   - Cleaning post_embeddings...")
        await session.execute(text(f"""
            DELETE FROM post_embeddings 
            WHERE post_id IN (SELECT id FROM posts_raw WHERE subreddit IN ('{formatted_list}'))
        """))
        
        # Dependency 3: Scores
        print("   - Cleaning post_scores...")
        # Check if table exists first to avoid error? Or just try. 
        # I saw it in the schema list.
        await session.execute(text(f"""
            DELETE FROM post_scores 
            WHERE post_id IN (SELECT id FROM posts_raw WHERE subreddit IN ('{formatted_list}'))
        """))
        
        # Dependency 4: Comments (Delete by subreddit is safer/faster)
        print("   - Cleaning comments...")
        await session.execute(text(f"""
            DELETE FROM comments WHERE subreddit IN ('{formatted_list}')
        """))

        # 4. Final Blow: Delete from Raw
        print("🔥 Deleting from main table (posts_raw)...")
        delete_sql = f"DELETE FROM posts_raw WHERE subreddit IN ('{formatted_list}')"
        await session.execute(text(delete_sql))
        
        await session.commit()
        print(f"✅ DEEP CLEAN COMPLETE. {count} posts and their roots destroyed/moved.")

    except Exception as e:
        print(f"❌ Purge failed: {e}")
        await session.rollback()
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(execute_purge())