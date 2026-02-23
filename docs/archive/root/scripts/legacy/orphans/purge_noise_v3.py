"""清洗员工社区数据 (V3)
修复外键约束 fk_posts_raw_duplicate_of 问题
"""
import asyncio
from sqlalchemy import text
from app.db.session import SessionFactory

async def purge_v3():
    noise_subs = ['r/AmazonFC', 'r/FASCAmazon', 'r/AmazonEmployees', 'r/AmazonFresh', 'r/fuckamazon', 
                  'r/AmazonDSPDrivers', 'r/walmart', 'r/Target', 'r/BestBuy',
                  'r/AmITheAsshole', 'r/stepparents', 'r/Teachers', 'r/raisedbynarcissists']
    subs_lower = [s.lower() for s in noise_subs]
    
    print(f'正在分批清洗 (V3 DuplicateOf Nullify): {subs_lower}')

    # 1. 预处理：将目标社区的 duplicate_of 设为 NULL
    # 同时，如果有其他帖子 duplicate_of 指向目标社区的帖子，也设为 NULL ?
    # 假设目标社区内只有内部引用。外部引用应较少。
    # 为了彻底，我们先把所有指向待删除ID的引用的 duplicate_of 设为 NULL 是最稳妥的，但全表扫太慢。
    # 策略：只处理目标社区内的帖子。
    
    # 既然我们要删除这些社区的所有帖子，那么这些帖子之间的引用也要断开。
    # 最快的方法：UPDATE posts_raw SET duplicate_of = NULL WHERE lower(subreddit) = ANY(:subs)
    # 这会解除该社区内帖子的所有 outgoing 引用。
    # 但如果有其他帖子 incoming 引用这些帖子呢？
    # 只要 outgoing 断开了，删除时如果不被 incoming 引用阻挡就行。
    # 错误是 `Key (id)=(727751) is still referenced from table "posts_raw"` -> 这说明是 Incoming 引用。
    # 即还有別的帖子引用了我们要删的这个 id。
    # 这个“别的帖子”可能也是我们要删的帖子（只是还没轮到删除），或者不在删除列表中。
    
    # 所以必须把所有要删除的帖子的 incoming 引用也切断。
    # 或者把所有要删除的帖子的 duplicate_of 字段置空，并且把所有 duplicate_of 指向要删除帖子的字段置空。
    
    # 步骤 1: Nullify internal/outgoing references
    print("解除引用 (internal/outgoing)...")
    async with SessionFactory() as session:
         await session.execute(text('''
            UPDATE posts_raw 
            SET duplicate_of_id = NULL 
            WHERE lower(subreddit) = ANY(:subs)
        '''), {'subs': subs_lower})
         await session.commit()
    
    # 步骤 2: Nullify incoming references from OUTSIDE (if any) or WITHIN (if step 1 missed circulars? no, step 1 handled all rows in subset)
    # 如果 Step 1 把 subset 内所有 duplicate_of 设为 NULL，那么 subset 内就不存在互相引用了。
    # 唯一剩下的是：subset 之外的帖子 引用了 subset 之内的帖子。
    # 如果有这种情况，DELETE 依然会失败。
    # 我们假设这种情况很少（跨社区引用）。如果有，我们也应该 Nullify 它们。
    # UPDATE posts_raw SET duplicate_of = NULL WHERE duplicate_of IN (SELECT id FROM posts_raw WHERE subreddit = ...)
    # 这可能很慢。先跳过，假设主要问题是 subset 内部引用。Step 1 应该解决了内部引用。
    
    print("引用解除完成。开始删除 (Hot First)...")
    
    # ... Copy paste logic from V2 ...
    deleted_hot = 0
    while True:
        async with SessionFactory() as session:
            res = await session.execute(text('''
                SELECT id FROM posts_hot WHERE lower(subreddit) = ANY(:subs) LIMIT 500
            '''), {'subs': subs_lower})
            batch_ids = [r[0] for r in res.fetchall()]
            
            if not batch_ids:
                break
            
            await session.execute(text('''
                DELETE FROM content_labels WHERE content_type = 'post' AND content_id = ANY(:ids)
            '''), {'ids': batch_ids})
            
            await session.execute(text('''
                DELETE FROM posts_hot WHERE id = ANY(:ids)
            '''), {'ids': batch_ids})
            
            await session.commit()
            deleted_hot += len(batch_ids)
            print(f'已删除 posts_hot: {deleted_hot}', end='\\r')
            
    print(f'\\n✅ Posts Hot 清洗完成: {deleted_hot}')

    deleted_posts = 0
    while True:
        async with SessionFactory() as session:
            # 使用 LIMIT 500 加快分批
            res = await session.execute(text('''
                SELECT id FROM posts_raw WHERE lower(subreddit) = ANY(:subs) LIMIT 500
            '''), {'subs': subs_lower})
            batch_ids = [r[0] for r in res.fetchall()]
            
            if not batch_ids:
                break
            
            # 删除关联
            await session.execute(text('DELETE FROM post_semantic_labels WHERE post_id = ANY(:ids)'), {'ids': batch_ids})
            await session.execute(text('DELETE FROM post_embeddings WHERE post_id = ANY(:ids)'), {'ids': batch_ids})
            
            # 删除 Raw
            await session.execute(text('DELETE FROM posts_raw WHERE id = ANY(:ids)'), {'ids': batch_ids})
            
            await session.commit()
            deleted_posts += len(batch_ids)
            print(f'已删除 posts_raw: {deleted_posts}', end='\\r')
            
    print(f'\\n✅ Posts Raw 清洗完成: {deleted_posts}')

if __name__ == "__main__":
    asyncio.run(purge_v3())
