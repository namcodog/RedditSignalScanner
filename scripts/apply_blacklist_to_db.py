#!/usr/bin/env python3
"""
应用黑名单配置到数据库

读取 config/community_blacklist.yaml，更新 community_pool 表的黑名单字段。

使用方法:
    PYTHONPATH=backend python3 scripts/apply_blacklist_to_db.py [--dry-run]
"""
import asyncio
import sys
from datetime import datetime, timezone

from sqlalchemy import select, update

from app.db.session import SessionFactory
from app.models.community_pool import CommunityPool
from app.services.blacklist_loader import get_blacklist_config


async def apply_blacklist(dry_run: bool = False) -> None:
    """应用黑名单配置到数据库"""
    # 加载黑名单配置
    config = get_blacklist_config()
    
    print(f"📋 黑名单配置:")
    print(f"   - 黑名单社区: {len(config.blacklisted_communities)} 个")
    print(f"   - 降权社区: {len(config.downranked_communities)} 个")
    
    async with SessionFactory() as db:
        # 获取所有社区
        result = await db.execute(select(CommunityPool))
        all_communities = result.scalars().all()
        print(f"\n📊 数据库现有社区: {len(all_communities)} 个")
        
        blacklisted_count = 0
        downranked_count = 0
        cleared_count = 0
        
        for community in all_communities:
            name = community.name
            
            # 检查是否在黑名单中
            if config.is_community_blacklisted(name):
                if not dry_run:
                    community.is_blacklisted = True
                    community.blacklist_reason = "blacklisted (from config)"
                    community.is_active = False  # 黑名单社区设为不活跃
                blacklisted_count += 1
                print(f"  🚫 黑名单: {name}")
            
            # 检查是否被降权
            elif config.is_community_downranked(name):
                downrank_factor = config.get_community_downrank_factor(name)
                reason = config.downranked_communities.get(name.lower(), {}).get("reason", "")
                
                if not dry_run:
                    community.is_blacklisted = False
                    community.downrank_factor = downrank_factor
                    community.blacklist_reason = f"downranked: {reason}"
                downranked_count += 1
                print(f"  ⬇️  降权: {name} (factor={downrank_factor})")
            
            # 清除之前的黑名单标记（如果不在当前配置中）
            elif community.is_blacklisted or community.downrank_factor is not None:
                if not dry_run:
                    community.is_blacklisted = False
                    community.blacklist_reason = None
                    community.downrank_factor = None
                    community.is_active = True
                cleared_count += 1
                print(f"  ✅ 清除标记: {name}")
        
        if dry_run:
            print(f"\n🔍 DRY RUN 模式 - 不会实际写入数据库")
        else:
            await db.commit()
            print(f"\n✅ 数据库更新完成")
        
        print(f"\n{'='*60}")
        print(f"📊 统计:")
        print(f"   - 黑名单社区: {blacklisted_count}")
        print(f"   - 降权社区: {downranked_count}")
        print(f"   - 清除标记: {cleared_count}")
        print(f"   - 未变更: {len(all_communities) - blacklisted_count - downranked_count - cleared_count}")


async def main() -> None:
    """主函数"""
    dry_run = "--dry-run" in sys.argv
    
    if dry_run:
        print("🔍 DRY RUN 模式启用\n")
    
    await apply_blacklist(dry_run=dry_run)


if __name__ == "__main__":
    asyncio.run(main())

