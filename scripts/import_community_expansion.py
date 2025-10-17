#!/usr/bin/env python3
"""
导入 200 个新社区到 community_pool 表

使用方法:
    PYTHONPATH=backend python3 scripts/import_community_expansion.py [--dry-run]
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.session import SessionFactory
from app.models.community_pool import CommunityPool


async def import_communities(dry_run: bool = False) -> None:
    """导入社区到数据库"""
    # 读取 JSON 文件
    json_path = Path("backend/data/community_expansion_200.json")
    if not json_path.exists():
        print(f"❌ 文件不存在: {json_path}")
        sys.exit(1)

    communities = json.loads(json_path.read_text())
    print(f"📄 读取到 {len(communities)} 个社区")

    async with SessionFactory() as db:
        # 检查现有社区
        result = await db.execute(select(CommunityPool.name))
        existing_names = {row[0] for row in result}
        print(f"📊 数据库现有社区: {len(existing_names)} 个")

        # 过滤已存在的社区
        new_communities = [c for c in communities if c["name"] not in existing_names]
        skipped = len(communities) - len(new_communities)
        
        if skipped > 0:
            print(f"⚠️  跳过 {skipped} 个已存在的社区")
        
        if not new_communities:
            print("✅ 所有社区已存在，无需导入")
            return

        print(f"🆕 准备导入 {len(new_communities)} 个新社区")

        if dry_run:
            print("\n🔍 DRY RUN 模式 - 不会实际写入数据库")
            print("\n前 5 个待导入社区示例:")
            for c in new_communities[:5]:
                print(f"  - {c['name']} ({c['tier']}) | {c['categories']}")
            return

        # 批量导入
        imported_count = 0
        failed = []

        for community in new_communities:
            try:
                # 准备数据
                data = {
                    "name": community["name"],
                    "tier": community["tier"],
                    "categories": community["categories"],
                    "description_keywords": community["description_keywords"],
                    "daily_posts": community.get("daily_posts", 0),
                    "avg_comment_length": 0,  # 默认值
                    "quality_score": community.get("quality_score", 0.70),
                    "priority": community["tier"],  # 使用 tier 作为 priority
                    "user_feedback_count": 0,
                    "discovered_count": 0,
                    "is_active": True,
                }

                # 插入或更新
                stmt = (
                    pg_insert(CommunityPool)
                    .values(**data)
                    .on_conflict_do_update(
                        index_elements=["name"],
                        set_={
                            "tier": data["tier"],
                            "categories": data["categories"],
                            "description_keywords": data["description_keywords"],
                            "daily_posts": data["daily_posts"],
                            "quality_score": data["quality_score"],
                            "priority": data["priority"],
                            "updated_at": datetime.now(timezone.utc),
                        },
                    )
                )
                await db.execute(stmt)
                imported_count += 1

                if imported_count % 20 == 0:
                    print(f"  ✓ 已导入 {imported_count}/{len(new_communities)}...")

            except Exception as e:
                failed.append((community["name"], str(e)))
                print(f"  ❌ 导入失败: {community['name']} - {e}")

        # 提交事务
        await db.commit()

        print(f"\n{'='*60}")
        print(f"✅ 导入完成！")
        print(f"   成功: {imported_count}")
        print(f"   失败: {len(failed)}")
        print(f"   跳过: {skipped}")
        
        if failed:
            print(f"\n失败详情:")
            for name, error in failed:
                print(f"  - {name}: {error}")

        # 验证最终数量
        result = await db.execute(select(CommunityPool))
        total = len(result.all())
        print(f"\n📊 数据库总社区数: {total}")


async def main() -> None:
    """主函数"""
    dry_run = "--dry-run" in sys.argv
    
    if dry_run:
        print("🔍 DRY RUN 模式启用")
    
    await import_communities(dry_run=dry_run)


if __name__ == "__main__":
    asyncio.run(main())

