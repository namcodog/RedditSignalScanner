#!/usr/bin/env python3
"""
同步黑名单配置到数据库

从 config/community_blacklist.yaml 读取黑名单社区配置，
并更新 community_pool 表的 is_blacklisted 和 blacklist_reason 字段。

使用方法:
    python3 scripts/sync_blacklist_to_db.py [--dry-run]

参数:
    --dry-run: 只显示将要更新的社区，不实际执行数据库更新
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

# 添加 backend 到路径
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.db.session import SessionFactory
from app.models.community_pool import CommunityPool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_blacklist_config(config_path: str = "config/community_blacklist.yaml") -> dict[str, Any]:
    """加载黑名单配置文件"""
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(config_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    return config


def extract_blacklisted_communities(config: dict[str, Any]) -> list[dict[str, str]]:
    """
    从配置中提取黑名单社区列表
    
    Returns:
        [{"name": "FreeKarma4U", "reason": "karma farming, spam"}, ...]
    """
    blacklisted = []
    seen_names = set()
    
    for item in config.get("blacklisted_communities", []):
        name = item.get("name", "").strip()
        reason = item.get("reason", "blacklisted")
        
        if not name:
            continue
        
        # 去重（配置文件中 The_Donald 出现了两次）
        if name.lower() in seen_names:
            logger.warning(f"⚠️ 重复的黑名单社区: {name}，跳过")
            continue
        
        seen_names.add(name.lower())
        blacklisted.append({"name": name, "reason": reason})
    
    return blacklisted


async def sync_blacklist_to_database(
    blacklisted_communities: list[dict[str, str]],
    dry_run: bool = False
) -> dict[str, Any]:
    """
    同步黑名单配置到数据库
    
    Args:
        blacklisted_communities: 黑名单社区列表
        dry_run: 是否为试运行模式（不实际更新数据库）
    
    Returns:
        统计信息字典
    """
    stats = {
        "total_blacklisted": len(blacklisted_communities),
        "updated": 0,
        "not_found": 0,
        "already_blacklisted": 0,
        "errors": []
    }
    
    async with SessionFactory() as db:
        # 1. 查询所有社区池中的社区
        result = await db.execute(
            select(CommunityPool.name, CommunityPool.is_blacklisted)
        )
        existing_communities = {
            row.name.lower(): row.is_blacklisted 
            for row in result.all()
        }
        
        logger.info(f"📊 社区池总数: {len(existing_communities)}")
        logger.info(f"📋 黑名单配置数: {len(blacklisted_communities)}")
        
        # 2. 准备批量更新数据
        communities_to_update = []
        
        for item in blacklisted_communities:
            name = item["name"]
            reason = item["reason"]
            
            # 检查社区是否存在于社区池
            if name.lower() not in existing_communities:
                logger.warning(f"⚠️ 社区不在社区池中: {name}")
                stats["not_found"] += 1
                continue
            
            # 检查是否已经是黑名单
            if existing_communities[name.lower()]:
                logger.debug(f"✓ 社区已在黑名单中: {name}")
                stats["already_blacklisted"] += 1
                continue
            
            communities_to_update.append({
                "name": name,
                "reason": reason
            })
        
        if not communities_to_update:
            logger.info("✅ 没有需要更新的社区")
            return stats
        
        logger.info(f"🔄 准备更新 {len(communities_to_update)} 个社区")
        
        if dry_run:
            logger.info("🔍 试运行模式，不会实际更新数据库")
            for item in communities_to_update:
                logger.info(f"  - {item['name']}: {item['reason']}")
            stats["updated"] = len(communities_to_update)
            return stats
        
        # 3. 批量更新数据库
        try:
            for item in communities_to_update:
                stmt = (
                    update(CommunityPool)
                    .where(CommunityPool.name == item["name"])
                    .values(
                        is_blacklisted=True,
                        blacklist_reason=item["reason"]
                    )
                )
                result = await db.execute(stmt)
                
                if result.rowcount > 0:
                    logger.info(f"✅ 已更新: {item['name']} - {item['reason']}")
                    stats["updated"] += 1
                else:
                    logger.error(f"❌ 更新失败: {item['name']}")
                    stats["errors"].append(item["name"])
            
            await db.commit()
            logger.info(f"✅ 批量更新完成，共更新 {stats['updated']} 个社区")
            
        except Exception as e:
            await db.rollback()
            logger.error(f"❌ 批量更新失败: {e}")
            stats["errors"].append(str(e))
            raise
    
    return stats


async def verify_blacklist_sync() -> dict[str, Any]:
    """验证黑名单同步结果"""
    async with SessionFactory() as db:
        result = await db.execute(
            select(
                CommunityPool.name,
                CommunityPool.is_blacklisted,
                CommunityPool.blacklist_reason
            ).where(CommunityPool.is_blacklisted == True)
        )
        
        blacklisted = result.all()
        
        logger.info(f"\n📊 验证结果:")
        logger.info(f"数据库中黑名单社区总数: {len(blacklisted)}")
        
        for row in blacklisted:
            logger.info(f"  - {row.name}: {row.blacklist_reason}")
        
        return {
            "total_blacklisted": len(blacklisted),
            "communities": [
                {"name": row.name, "reason": row.blacklist_reason}
                for row in blacklisted
            ]
        }


async def main(dry_run: bool = False) -> None:
    """主函数"""
    logger.info("🚀 开始同步黑名单配置到数据库")
    logger.info("=" * 60)
    
    try:
        # 1. 加载配置文件
        config = load_blacklist_config()
        logger.info(f"✅ 配置文件加载成功")
        
        # 2. 提取黑名单社区
        blacklisted_communities = extract_blacklisted_communities(config)
        logger.info(f"✅ 提取到 {len(blacklisted_communities)} 个黑名单社区")
        
        # 3. 同步到数据库
        stats = await sync_blacklist_to_database(blacklisted_communities, dry_run)
        
        # 4. 打印统计信息
        logger.info("\n" + "=" * 60)
        logger.info("📊 同步统计:")
        logger.info(f"  - 配置文件中黑名单总数: {stats['total_blacklisted']}")
        logger.info(f"  - 已更新: {stats['updated']}")
        logger.info(f"  - 已在黑名单中: {stats['already_blacklisted']}")
        logger.info(f"  - 不在社区池中: {stats['not_found']}")
        if stats['errors']:
            logger.error(f"  - 错误: {len(stats['errors'])}")
            for error in stats['errors']:
                logger.error(f"    - {error}")
        
        # 5. 验证结果
        if not dry_run:
            logger.info("\n" + "=" * 60)
            logger.info("🔍 验证黑名单同步结果...")
            verify_result = await verify_blacklist_sync()
            
            # 验收标准检查
            if verify_result["total_blacklisted"] == stats["total_blacklisted"]:
                logger.info(f"✅ 验收通过: 数据库中黑名单社区数 = {verify_result['total_blacklisted']}")
            else:
                logger.warning(
                    f"⚠️ 验收警告: 预期 {stats['total_blacklisted']} 个，"
                    f"实际 {verify_result['total_blacklisted']} 个"
                )
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ 黑名单同步完成！")
        
    except Exception as e:
        logger.error(f"❌ 同步失败: {e}")
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="同步黑名单配置到数据库")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试运行模式，不实际更新数据库"
    )
    
    args = parser.parse_args()
    
    asyncio.run(main(dry_run=args.dry_run))

