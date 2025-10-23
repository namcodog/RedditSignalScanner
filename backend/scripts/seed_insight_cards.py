"""
生成洞察卡片测试数据

用于验证洞察卡片 v0 功能
"""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta

from app.db.session import SessionFactory
from app.models.user import User, MembershipLevel
from app.models.task import Task, TaskStatus
from app.models.insight import InsightCard, Evidence
from app.core.security import hash_password
from sqlalchemy import select


async def seed_insight_cards():
    """生成洞察卡片测试数据"""
    
    async with SessionFactory() as db:
        # 1. 确保测试用户存在
        result = await db.execute(select(User).where(User.email == "test@example.com"))
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                email="test@example.com",
                password_hash=hash_password("test123456"),
                membership_level=MembershipLevel.PRO,
                is_active=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print(f"✅ 创建测试用户: {user.email}")
        else:
            print(f"✅ 测试用户已存在: {user.email}")
        
        # 2. 创建一个已完成的任务
        task = Task(
            user_id=user.id,
            product_description="AI agent that summarises Reddit market signals for go-to-market teams.",
            status=TaskStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        print(f"✅ 创建任务: {task.id}")
        
        # 3. 创建洞察卡片
        insight_cards_data = [
            {
                "title": "用户痛点：手动追踪 Reddit 讨论耗时且低效",
                "summary": "许多产品团队和市场研究人员表示，手动浏览 Reddit 子版块来追踪用户反馈和市场趋势非常耗时。他们需要每天花费 2-3 小时浏览多个子版块，但仍然容易错过重要讨论。",
                "confidence": 0.92,
                "time_window_days": 30,
                "subreddits": ["r/startups", "r/ProductManagement", "r/SaaS"],
                "evidences": [
                    {
                        "post_url": "https://reddit.com/r/startups/comments/abc123",
                        "excerpt": "I spend 3 hours every day manually checking r/startups, r/entrepreneur, and r/SaaS for mentions of our product category. It's exhausting and I know I'm missing important threads.",
                        "timestamp": datetime.now(timezone.utc) - timedelta(days=5),
                        "subreddit": "r/startups",
                        "score": 0.95,
                    },
                    {
                        "post_url": "https://reddit.com/r/ProductManagement/comments/def456",
                        "excerpt": "Our team tried to track Reddit feedback manually but gave up after a week. Too many subreddits, too much noise.",
                        "timestamp": datetime.now(timezone.utc) - timedelta(days=12),
                        "subreddit": "r/ProductManagement",
                        "score": 0.88,
                    },
                    {
                        "post_url": "https://reddit.com/r/SaaS/comments/ghi789",
                        "excerpt": "I wish there was a tool that could automatically scan Reddit for market signals. Manual tracking is not scalable.",
                        "timestamp": datetime.now(timezone.utc) - timedelta(days=18),
                        "subreddit": "r/SaaS",
                        "score": 0.91,
                    },
                ],
            },
            {
                "title": "竞品分析：Notion AI 和 Coda 在自动化工作流方面获得关注",
                "summary": "Reddit 用户频繁讨论 Notion AI 和 Coda 作为自动化工作流的工具。用户特别喜欢 Notion AI 的自动摘要功能和 Coda 的数据集成能力。",
                "confidence": 0.85,
                "time_window_days": 30,
                "subreddits": ["r/productivity", "r/notion", "r/SaaS"],
                "evidences": [
                    {
                        "post_url": "https://reddit.com/r/productivity/comments/jkl012",
                        "excerpt": "Notion AI's auto-summarization feature is a game changer. I can now process 10x more content in the same time.",
                        "timestamp": datetime.now(timezone.utc) - timedelta(days=8),
                        "subreddit": "r/productivity",
                        "score": 0.87,
                    },
                    {
                        "post_url": "https://reddit.com/r/notion/comments/mno345",
                        "excerpt": "Coda's integration with external data sources is impressive. We use it to pull in Reddit data automatically.",
                        "timestamp": datetime.now(timezone.utc) - timedelta(days=15),
                        "subreddit": "r/notion",
                        "score": 0.82,
                    },
                ],
            },
            {
                "title": "市场机会：自动化 Reddit 信号检测的需求强烈",
                "summary": "多个子版块的用户表达了对自动化 Reddit 信号检测工具的强烈需求。他们希望工具能够自动识别趋势、提取痛点、发现竞品，并提供可操作的洞察。",
                "confidence": 0.89,
                "time_window_days": 30,
                "subreddits": ["r/startups", "r/entrepreneur", "r/marketing"],
                "evidences": [
                    {
                        "post_url": "https://reddit.com/r/startups/comments/pqr678",
                        "excerpt": "I would pay $100/month for a tool that automatically scans Reddit for market signals and competitor mentions.",
                        "timestamp": datetime.now(timezone.utc) - timedelta(days=3),
                        "subreddit": "r/startups",
                        "score": 0.93,
                    },
                    {
                        "post_url": "https://reddit.com/r/entrepreneur/comments/stu901",
                        "excerpt": "Reddit is a goldmine for market research, but we need better tools to extract insights automatically.",
                        "timestamp": datetime.now(timezone.utc) - timedelta(days=10),
                        "subreddit": "r/entrepreneur",
                        "score": 0.86,
                    },
                    {
                        "post_url": "https://reddit.com/r/marketing/comments/vwx234",
                        "excerpt": "Our marketing team spends too much time on Reddit. We need automation to scale our research efforts.",
                        "timestamp": datetime.now(timezone.utc) - timedelta(days=20),
                        "subreddit": "r/marketing",
                        "score": 0.88,
                    },
                ],
            },
        ]
        
        for card_data in insight_cards_data:
            evidences_data = card_data.pop("evidences")
            
            insight_card = InsightCard(
                task_id=task.id,
                **card_data,
            )
            db.add(insight_card)
            await db.flush()  # 获取 insight_card.id
            
            for evidence_data in evidences_data:
                evidence = Evidence(
                    insight_card_id=insight_card.id,
                    **evidence_data,
                )
                db.add(evidence)
            
            print(f"✅ 创建洞察卡片: {insight_card.title}")
        
        await db.commit()
        
        print(f"\n🎉 洞察卡片测试数据生成完成！")
        print(f"📋 任务 ID: {task.id}")
        print(f"🔗 访问洞察卡片页面: http://localhost:3006/insights/{task.id}")
        print(f"👤 测试账号: test@example.com / test123456")


if __name__ == "__main__":
    asyncio.run(seed_insight_cards())

