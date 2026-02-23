#!/usr/bin/env python3
"""
Backfill sentiment scores for existing content_labels records.
Uses VADER sentiment analysis.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.core.config import get_settings

BATCH_SIZE = 1000
_vader = SentimentIntensityAnalyzer()


def compute_sentiment(text_content: str) -> tuple[float, str]:
    """Compute VADER sentiment score and label."""
    if not text_content:
        return 0.0, "neutral"
    
    vs = _vader.polarity_scores(text_content)
    compound = vs.get("compound", 0.0)
    
    if compound >= 0.05:
        label = "positive"
    elif compound <= -0.05:
        label = "negative"
    else:
        label = "neutral"
    
    return compound, label


async def backfill_posts(engine):
    """Backfill sentiment for post-type labels."""
    print("\n=== Backfilling POST sentiment ===")
    
    async with engine.begin() as conn:
        # Count total
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM content_labels 
            WHERE content_type = 'post' AND sentiment_score IS NULL
        """))
        total = result.scalar()
        print(f"Total posts to backfill: {total}")
        
        if total == 0:
            return
        
        processed = 0
        while True:
            # Fetch batch with text content
            result = await conn.execute(text("""
                SELECT cl.id, pr.title, pr.body
                FROM content_labels cl
                JOIN posts_raw pr ON cl.content_id = pr.id
                WHERE cl.content_type = 'post' AND cl.sentiment_score IS NULL
                LIMIT :batch
            """), {"batch": BATCH_SIZE})
            
            rows = result.fetchall()
            if not rows:
                break
            
            # Process batch
            updates = []
            for row in rows:
                label_id = row[0]
                title = row[1] or ""
                body = row[2] or ""
                text_content = f"{title}\n{body}"
                
                score, label = compute_sentiment(text_content)
                updates.append({"id": label_id, "score": score, "label": label})
            
            # Batch update
            for upd in updates:
                await conn.execute(text("""
                    UPDATE content_labels 
                    SET sentiment_score = :score, sentiment_label = :label
                    WHERE id = :id
                """), upd)
            
            processed += len(rows)
            print(f"  Processed {processed}/{total} posts...")
    
    print(f"✅ Posts backfill complete: {processed} records")


async def backfill_comments(engine):
    """Backfill sentiment for comment-type labels."""
    print("\n=== Backfilling COMMENT sentiment ===")
    
    async with engine.begin() as conn:
        # Count total
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM content_labels 
            WHERE content_type = 'comment' AND sentiment_score IS NULL
        """))
        total = result.scalar()
        print(f"Total comments to backfill: {total}")
        
        if total == 0:
            return
        
        processed = 0
        while True:
            # Fetch batch with text content
            result = await conn.execute(text("""
                SELECT cl.id, c.body
                FROM content_labels cl
                JOIN comments c ON cl.content_id = c.id
                WHERE cl.content_type = 'comment' AND cl.sentiment_score IS NULL
                LIMIT :batch
            """), {"batch": BATCH_SIZE})
            
            rows = result.fetchall()
            if not rows:
                break
            
            # Process batch
            updates = []
            for row in rows:
                label_id = row[0]
                body = row[1] or ""
                
                score, label = compute_sentiment(body)
                updates.append({"id": label_id, "score": score, "label": label})
            
            # Batch update
            for upd in updates:
                await conn.execute(text("""
                    UPDATE content_labels 
                    SET sentiment_score = :score, sentiment_label = :label
                    WHERE id = :id
                """), upd)
            
            processed += len(rows)
            print(f"  Processed {processed}/{total} comments...")
    
    print(f"✅ Comments backfill complete: {processed} records")


async def main():
    print("Starting sentiment backfill...")
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    
    await backfill_posts(engine)
    await backfill_comments(engine)
    
    print("\n🎉 All sentiment backfill complete!")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
