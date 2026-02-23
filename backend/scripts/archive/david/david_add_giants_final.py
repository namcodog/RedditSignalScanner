import sys
import os
import asyncio
import json
from sqlalchemy import text
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory
from app.db.sequence_repair import repair_serial_pk_sequence

async def inject_giants_robust():
    session = SessionFactory()
    try:
        print("--- 🚀 执行全量注入 (Robust Injection) ---")
        print("   原则：只新增缺失数据，不改动已有社区配置。")

        # 0) Repair sequence drift first (safe: only moves forward, does not touch table data)
        try:
            result = await repair_serial_pk_sequence(
                session,
                table_regclass="public.community_pool",
                pk_column="id",
            )
            print(
                "   - ✅ 已修复发号器："
                f"max_id={result.table_max_id}, "
                f"next(before)={result.sequence_previous_next} -> next(after)={result.sequence_new_next}"
            )
        except Exception as exc:
            print(f"   - ⚠️ 跳过发号器修复（不阻断后续插入）：{exc}")
        
        # 26 Communities
        raw_recruits = [
            # 1. AI Workflow (New Vertical)
            ('r/LocalLLaMA', 'AI_Workflow'),
            ('r/ChatGPT', 'AI_Workflow'),
            ('r/StableDiffusion', 'AI_Workflow'),
            ('r/PromptEngineering', 'AI_Workflow'),
            ('r/automation', 'AI_Workflow'),
            
            # 2. Life Aesthetics -> Home_Lifestyle
            ('r/MaleLivingSpace', 'Home_Lifestyle'),
            ('r/FemaleLivingSpace', 'Home_Lifestyle'),
            ('r/CozyPlaces', 'Home_Lifestyle'),
            ('r/AmateurRoomPorn', 'Home_Lifestyle'),
            
            # 3. Yard/Home Maintenance -> Home_Lifestyle
            ('r/lawncare', 'Home_Lifestyle'),
            ('r/hvac', 'Home_Lifestyle'),
            ('r/cleaning', 'Home_Lifestyle'),
            ('r/organization', 'Home_Lifestyle'),
            ('r/ReefTank', 'Home_Lifestyle'),
            ('r/Aquariums', 'Home_Lifestyle'),
            
            # 4. Pets -> Family_Parenting
            ('r/dogs', 'Family_Parenting'),
            ('r/cats', 'Family_Parenting'),
            ('r/puppy101', 'Family_Parenting'),
            ('r/pets', 'Family_Parenting'),
            
            # 5. Digital/Setup -> Tools_EDC
            ('r/battlestations', 'Tools_EDC'),
            ('r/desksetup', 'Tools_EDC'),
            ('r/homeoffice', 'Tools_EDC'),
            ('r/askelectronics', 'Tools_EDC'),
            ('r/justrolledintotheshop', 'Tools_EDC'),
            
            # 6. Kitchen -> Food_Coffee
            ('r/airfryer', 'Food_Coffee_Lifestyle'),
            ('r/instantpot', 'Food_Coffee_Lifestyle'),
            ('r/saas', 'Ecommerce_Business')
        ]
        
        added_pool = 0
        added_cache = 0
        skipped_pool = 0
        skipped_cache = 0
        
        for raw_name, vertical in raw_recruits:
            name = raw_name.lower() # Strict lowercase
            
            # --- 1. Community Pool Injection ---
            res = await session.execute(
                text("SELECT 1 FROM community_pool WHERE name = :name"),
                {"name": name},
            )
            
            if res.fetchone():
                print(f"  - [Pool] {name} 已存在，跳过（不改动现有数据）。")
                skipped_pool += 1
            else:
                print(f"  - [Pool] Inserting {name}...")
                insert_sql = """
                    INSERT INTO community_pool (
                        name, vertical, tier, is_active, is_blacklisted,
                        created_at, updated_at, 
                        categories, description_keywords, 
                        semantic_quality_score, priority, health_status,
                        daily_posts, avg_comment_length, user_feedback_count, 
                        discovered_count, auto_tier_enabled
                    )
                    VALUES (
                        :name, :vertical, 'high', true, false,
                        NOW(), NOW(), 
                        CAST(:categories AS jsonb), CAST(:keywords AS jsonb),
                        0.85, 'high', 'healthy',
                        0, 0, 0, 0, false
                    )
                """
                await session.execute(
                    text(insert_sql),
                    {
                        "name": name,
                        "vertical": vertical,
                        "categories": json.dumps([vertical]),
                        "keywords": json.dumps({"seed": "david_add_giants_final"}),
                    },
                )
                added_pool += 1
            
            # --- 2. Community Cache Injection ---
            res_c = await session.execute(
                text("SELECT 1 FROM community_cache WHERE community_name = :name"),
                {"name": name},
            )
            
            if not res_c.fetchone():
                print(f"  - [Cache] Inserting stub for {name}...")
                # FIXED: quality_score -> crawl_quality_score
                cache_insert = """
                    INSERT INTO community_cache (
                        community_name, member_count, last_crawled_at, 
                        created_at, updated_at, 
                        posts_cached, crawl_quality_score, hit_count,
                        crawl_priority, crawl_frequency_hours, is_active,
                        empty_hit, success_hit, failure_hit, avg_valid_posts,
                        total_posts_fetched, quality_tier, ttl_seconds
                    )
                    VALUES (
                        :name, 0, NOW(), 
                        NOW(), NOW(), 
                        0, 0.5, 0,
                        50, 2, true,
                        0, 0, 0, 0,
                        0, 'medium', 3600
                    )
                """
                await session.execute(text(cache_insert), {"name": name})
                added_cache += 1
            else:
                skipped_cache += 1

        await session.commit()
        print(f"\n✅ SUCCESS.")
        print(f"   - Pool Inserted: {added_pool} (Skipped existing: {skipped_pool})")
        print(f"   - Cache Inserted: {added_cache}")
        print(f"   - Cache Skipped existing: {skipped_cache}")

    except Exception as e:
        print(f"❌ CRITICAL FAILURE: {e}")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(inject_giants_robust())
