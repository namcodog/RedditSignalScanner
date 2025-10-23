#!/usr/bin/env python3
"""
测试置信度计算功能

这个脚本会：
1. 创建一个测试任务
2. 手动触发分析
3. 验证置信度是否正确计算和存储
"""

import asyncio
import uuid
from datetime import datetime, UTC

from sqlalchemy import select

from app.db.session import SessionFactory
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.models.analysis import Analysis
from app.services.analysis_engine import run_analysis
from app.schemas.task import TaskSummary


async def main():
    print("=" * 80)
    print("🧪 测试置信度计算功能")
    print("=" * 80)
    
    async with SessionFactory() as session:
        # 1. 获取测试用户
        result = await session.execute(
            select(User).where(User.email == "test@example.com")
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print("❌ 测试用户不存在，请先创建 test@example.com")
            return
        
        print(f"\n✅ 找到测试用户: {user.email}")
        
        # 2. 创建测试任务
        task = Task(
            id=uuid.uuid4(),
            user_id=user.id,
            product_description="一款专为自由职业者设计的时间追踪和发票管理工具，自动记录工作时间，生成专业发票，并集成主流支付平台。",
            status=TaskStatus.PENDING,
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        
        print(f"\n✅ 创建测试任务: {task.id}")
        
        # 3. 运行分析
        print(f"\n🔄 开始分析...")
        task_summary = TaskSummary(
            id=task.id,
            user_id=task.user_id,
            product_description=task.product_description,
            status=task.status,
            created_at=task.created_at,
        )
        
        try:
            result = await run_analysis(task_summary)
            print(f"\n✅ 分析完成！")
            print(f"  - 置信度: {result.confidence_score:.2f}")
            print(f"  - 社区数: {len(result.sources.get('communities', []))}")
            print(f"  - 帖子数: {result.sources.get('posts_analyzed', 0)}")
            print(f"  - 痛点数: {len(result.insights.get('pain_points', []))}")
            print(f"  - 竞品数: {len(result.insights.get('competitors', []))}")
            print(f"  - 机会数: {len(result.insights.get('opportunities', []))}")
            
            # 4. 保存分析结果
            analysis = Analysis(
                task=task,
                insights=result.insights,
                sources=result.sources,
                confidence_score=result.confidence_score,
                analysis_version=1,
            )
            session.add(analysis)
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(UTC)
            
            await session.commit()
            await session.refresh(analysis)
            
            print(f"\n✅ 分析结果已保存到数据库")
            print(f"  - Analysis ID: {analysis.id}")
            print(f"  - 数据库中的置信度: {analysis.confidence_score}")
            
        except Exception as e:
            print(f"\n❌ 分析失败: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # 5. 验证数据库中的数据
        print(f"\n🔍 验证数据库中的数据...")
        result = await session.execute(
            select(Analysis).where(Analysis.task_id == task.id)
        )
        db_analysis = result.scalar_one_or_none()
        
        if db_analysis and db_analysis.confidence_score is not None:
            print(f"\n✅ 验证成功！")
            print(f"  - 任务ID: {task.id}")
            print(f"  - 置信度: {db_analysis.confidence_score}")
            print(f"\n🎉 置信度功能正常工作！")
        else:
            print(f"\n❌ 验证失败：数据库中的置信度为 None")


if __name__ == "__main__":
    asyncio.run(main())

