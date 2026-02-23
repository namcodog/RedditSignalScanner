import sys
import os
import json
import asyncio
from sqlalchemy import text
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory

async def cleanup_and_hunt():
    session = SessionFactory()
    
    # Updated kill list including r/askwomen
    kill_list = [
        'r/instacartshoppers', 
        'r/amazondspdrivers', 
        'r/amazonflexdrivers', 
        'r/walmartemployees', 
        'r/amazonemployees', 
        'r/fascamazon', 
        'r/vent', 
        'r/trueoffmychest', 
        'r/sideproject',
        'r/askwomen' 
    ]

    try:
        print("--- 🧹 正在清理社区缓存 (Cleaning Community Cache) ---")
        
        # 1. Clean DB Table community_cache
        formatted_list = "', '".join(kill_list)
        sql = f"DELETE FROM community_cache WHERE community_name IN ('{formatted_list}')"
        result = await session.execute(text(sql))
        await session.commit()
        print(f"✅ 从数据库缓存表 (community_cache) 移除了 {result.rowcount} 条记录。")

        # 2. Clean JSON File (crawl_progress.json)
        # Check current dir first, then backend/
        json_path = 'crawl_progress.json'
        if not os.path.exists(json_path):
             json_path = 'backend/crawl_progress.json'

        if os.path.exists(json_path):
            print(f"📄 正在检查进度文件 ({json_path})...")
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                
                removed_count = 0
                for sub in kill_list:
                    if sub in data:
                        del data[sub]
                        removed_count += 1
                
                if removed_count > 0:
                    with open(json_path, 'w') as f:
                        json.dump(data, f, indent=2)
                    print(f"✅ 从 JSON 文件中移除了 {removed_count} 个社区。")
                else:
                    print("✅ JSON 文件中未发现这些社区（干净）。")
            except Exception as e:
                print(f"⚠️ 读取/写入 JSON 失败: {e}")
        else:
            print("⚠️ 未找到 crawl_progress.json，跳过。")

        # 3. Hunt Round 2 (Excluding known blacklisted)
        print("\n--- 🕵️‍♂️ 再次巡查 (Re-Hunting) ---")
        suspicious_keywords = [
            'funny', 'meme', 'joke', 'gaming', 'game', 
            'politics', 'news', 'world', 
            'movie', 'film', 'tv', 'show', 'music', 
            'teen', 'school', 'college',
            'ask', 'chat', 'conversation'
        ]
        
        conditions = " OR ".join([f"name ILIKE '%{kw}%'" for kw in suspicious_keywords])
        hunt_sql = f"""
            SELECT name, vertical, categories 
            FROM community_pool 
            WHERE ({conditions}) 
            AND is_blacklisted = false 
            AND is_active = true
            ORDER BY name
        """
        
        result = await session.execute(text(hunt_sql))
        rows = result.fetchall()
        
        print(f"Found {len(rows)} potential NEW noise communities:")
        for row in rows:
            print(f"  - {row[0]} ({row[1]})")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(cleanup_and_hunt())