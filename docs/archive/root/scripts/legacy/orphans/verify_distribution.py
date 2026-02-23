"""验证清洗后的痛点分布 (Comments + Posts)"""
import asyncio
from sqlalchemy import text
from app.db.session import SessionFactory

async def check():
    async with SessionFactory() as session:
        # 1. 检查 Employees 是否真的删了
        res = await session.execute(text("SELECT COUNT(*) FROM posts_raw WHERE lower(subreddit) = 'amazonfc'"))
        fc_cnt = res.scalar()
        print(f"r/AmazonFC 剩余帖子: {fc_cnt} (预期 0)")

        # 2. 分别统计 Comments 和 Posts
        for content_type in ['comment', 'post']:
            print(f'\n=== {content_type.upper()} 痛点分布 (Active Only) ===')
            
            if content_type == 'comment':
                query = '''
                    SELECT aspect, COUNT(*) as cnt
                    FROM content_labels cl
                    JOIN comments c ON c.id = cl.content_id
                    JOIN community_pool cp ON lower(cp.name) = lower(c.subreddit)
                    WHERE cl.category = 'pain'
                      AND cl.content_type = 'comment'
                      AND cp.is_active = true
                    GROUP BY aspect
                    ORDER BY cnt DESC
                '''
            else:
                query = '''
                    SELECT aspect, COUNT(*) as cnt
                    FROM content_labels cl
                    JOIN posts_raw p ON p.id = cl.content_id
                    JOIN community_pool cp ON lower(cp.name) = lower(p.subreddit)
                    WHERE cl.category = 'pain'
                      AND cl.content_type = 'post'
                      AND cp.is_active = true
                    GROUP BY aspect
                    ORDER BY cnt DESC
                '''
            
            result = await session.execute(text(query))
            rows = list(result.fetchall())
            total = sum(r[1] for r in rows)
            
            other_cnt = 0
            for row in rows:
                pct = row[1] / total * 100 if total > 0 else 0
                print(f'  {row[0]}: {row[1]:,} ({pct:.2f}%)')
                if row[0] == 'other':
                    other_cnt = row[1]
            
            print(f'  ---')
            print(f'  Total: {total:,}')
            print(f'  Other%: {other_cnt/total*100:.2f}%' if total > 0 else '  N/A')

if __name__ == "__main__":
    asyncio.run(check())
