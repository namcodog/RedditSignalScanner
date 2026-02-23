#!/usr/bin/env python3
"""
Relabel Needs (Survival, Growth, etc.) for all posts using updated SmartTagger logic.
"""
import asyncio
from app.services.semantic.smart_tagger import SemanticTagger
from app.db.session import SessionFactory
from sqlalchemy import text

async def relabel():
    tagger = SemanticTagger()
    
    async with SessionFactory() as session:
        # Get all post IDs
        print("Fetching posts...")
        rows = await session.execute(text("SELECT id FROM posts_raw WHERE is_current = true ORDER BY id DESC"))
        ids = [r.id for r in rows.fetchall()]
        print(f"Found {len(ids)} posts to relabel.")
        
        # Process in chunks
        chunk_size = 100
        total = len(ids)
        processed = 0
        
        # We can't use async with tagger because it uses sync engine internally (legacy code?)
        # SmartTagger uses its own synchronous engine.
        # But we can call process_single in loop.
        # Note: process_single creates its own connection each time. This is slow for 200k posts.
        # process_batch uses ONE connection for a batch. Better.
        
        # But process_batch selects NULL labels.
        # Let's verify SmartTagger.process_batch query.
        # Line 361: WHERE pr.is_current = true AND psl.post_id IS NULL
        
        # To force update, we should truncate post_semantic_labels?
        # Or modify process_batch to ignore existing labels?
        # Truncate is fastest way to "Reset".
        # Safe to truncate? It's derived data. Yes.
        
        print("Truncating post_semantic_labels to force full re-tagging...")
        await session.execute(text("TRUNCATE TABLE post_semantic_labels"))
        await session.commit()
        
        # Now process_batch will work
        print("Starting batch processing...")
        while True:
            res = tagger.process_batch(limit=1000)
            count = res["processed"]
            if count == 0:
                break
            processed += count
            print(f"Processed {processed}/{total}...")

    print("✅ Needs Relabeling Complete.")

if __name__ == "__main__":
    asyncio.run(relabel())
