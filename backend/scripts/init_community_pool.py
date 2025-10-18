#!/usr/bin/env python3
"""
初始化 community_pool 表 - 导入200个社区数据

用途：将 backend/data/community_expansion_200.json 中的200个社区导入到 community_pool 表
执行：python backend/scripts/init_community_pool.py
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.session import SessionFactory
from app.services.community_pool_loader import CommunityPoolLoader


async def main():
    """主函数：导入社区数据"""
    print("=" * 60)
    print("🚀 初始化 community_pool 表")
    print("=" * 60)
    print()
    
    # 1. 检查数据文件
    data_file = project_root / "data" / "community_expansion_200.json"
    print(f"📂 数据文件: {data_file}")
    
    if not data_file.exists():
        print(f"❌ 错误: 数据文件不存在: {data_file}")
        return 1
    
    # 读取并验证数据
    try:
        with open(data_file, "r", encoding="utf-8") as f:
            communities_data = json.load(f)
        
        if not isinstance(communities_data, list):
            print(f"❌ 错误: 数据格式不正确，应该是数组")
            return 1
        
        print(f"✅ 数据文件有效，包含 {len(communities_data)} 个社区")
        print()
    except Exception as e:
        print(f"❌ 错误: 读取数据文件失败 - {e}")
        return 1
    
    # 2. 连接数据库并导入
    print("📊 开始导入数据...")
    print()
    
    try:
        async with SessionFactory() as db:
            # 补充缺失的字段
            for community in communities_data:
                # 根据 tier 设置 priority
                if "priority" not in community:
                    tier = community.get("tier", "medium").lower()
                    if tier == "high":
                        community["priority"] = "high"
                    elif tier == "low":
                        community["priority"] = "low"
                    else:
                        community["priority"] = "medium"

                # 确保必需字段存在
                if "estimated_daily_posts" not in community:
                    community["estimated_daily_posts"] = community.get("daily_posts", 50)

                if "description_keywords" not in community:
                    community["description_keywords"] = []

            # 使用 CommunityPoolLoader 导入
            # 注意：需要将数据包装成 {"communities": [...]} 格式
            temp_file = project_root / "data" / "temp_seed_for_import.json"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump({"communities": communities_data}, f, ensure_ascii=False, indent=2)

            loader = CommunityPoolLoader(db, seed_path=temp_file)
            result = await loader.load_seed_communities()

            # 清理临时文件
            temp_file.unlink()
            
            print("✅ 导入完成！")
            print()
            print("📈 导入统计:")
            print(f"   总社区数:     {result.get('total', 0)}")
            print(f"   新增:         {result.get('loaded', 0)}")
            print(f"   更新:         {result.get('updated', 0)}")
            print(f"   跳过:         {result.get('skipped', 0)}")
            print(f"   黑名单:       {result.get('blacklisted', 0)}")
            print()
            
    except Exception as e:
        print(f"❌ 错误: 导入失败 - {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # 3. 验证导入结果
    print("🔍 验证导入结果...")
    print()
    
    try:
        async with SessionFactory() as db:
            from sqlalchemy import select, func
            from app.models.community_pool import CommunityPool
            
            # 统计总数
            result = await db.execute(select(func.count()).select_from(CommunityPool))
            total_count = result.scalar()
            
            # 按 tier 统计
            result = await db.execute(
                select(CommunityPool.tier, func.count())
                .group_by(CommunityPool.tier)
                .order_by(CommunityPool.tier)
            )
            tier_stats = result.all()
            
            # 统计活跃社区
            result = await db.execute(
                select(func.count())
                .select_from(CommunityPool)
                .where(CommunityPool.is_active == True)
            )
            active_count = result.scalar()
            
            print(f"✅ community_pool 表统计:")
            print(f"   总社区数:     {total_count}")
            print(f"   活跃社区:     {active_count}")
            print()
            print(f"   按 tier 分布:")
            for tier, count in tier_stats:
                print(f"     {tier:10s}: {count:3d} 个")
            print()
            
            if total_count >= 200:
                print("🎉 成功！已导入200个社区到 community_pool 表！")
                print()
                print("=" * 60)
                print("✅ 下一步: 重启 Celery 自动抓取系统")
                print("   命令: make warmup-clean-restart")
                print("=" * 60)
                return 0
            else:
                print(f"⚠️  警告: 导入的社区数量少于预期 (期望200，实际{total_count})")
                return 1
                
    except Exception as e:
        print(f"❌ 错误: 验证失败 - {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

