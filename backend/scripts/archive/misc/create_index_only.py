import sys
import os
import asyncio
from sqlalchemy import create_engine, text

# Add current directory to path to find app module
sys.path.append(os.getcwd())
from app.core.config import get_settings

async def create_missing_indexes():
    settings = get_settings()
    DATABASE_URL = settings.database_url

    # Use synchronous engine for DDL
    sync_db_url = DATABASE_URL.replace("postgresql+asyncpg", "postgresql+psycopg2")
    engine = create_engine(sync_db_url, isolation_level="AUTOCOMMIT")

    indexes_to_create = [
        {
            "name": "idx_posts_raw_duplicate_of",
            "table": "posts_raw",
            "column": "duplicate_of_id",
            "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_raw_duplicate_of ON posts_raw (duplicate_of_id);"
        },
        {
            "name": "idx_post_semantic_labels_post_id",
            "table": "post_semantic_labels",
            "column": "post_id",
            "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_post_semantic_labels_post_id ON post_semantic_labels (post_id);"
        },
        {
            "name": "idx_post_scores_post_id_full",
            "table": "post_scores",
            "column": "post_id",
            "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_post_scores_post_id_full ON post_scores (post_id);"
        },
        # Check post_embeddings too just in case
        {
            "name": "idx_post_embeddings_post_id",
            "table": "post_embeddings",
            "column": "post_id",
            "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_post_embeddings_post_id ON post_embeddings (post_id);"
        }
    ]

    print(f"--- 🛠  补全数据库索引 (Fixing Database Indexes) ---")
    
    with engine.connect() as connection:
        for idx in indexes_to_create:
            print(f"👉 正在创建/检查索引: {idx['name']} ...")
            try:
                connection.execute(text(idx['sql']))
                print(f"   ✅ 成功。")
            except Exception as e:
                print(f"   ❌ 失败: {e}")
        
    print(f"--- ✅ 所有索引检查完毕 ---")

if __name__ == "__main__":
    asyncio.run(create_missing_indexes())
