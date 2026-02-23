
import sys
import os
import asyncio
from sqlalchemy import text
from app.core.config import get_settings
from app.services.text_classifier import classify_category_aspect, TextClassifier

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

async def verify():
    print("1. Testing TextClassifier VADER integration...")
    positive_text = "I love this product! It is amazing and works perfectly."
    negative_text = "This is terrible. The shipping was delayed and it arrived broken."
    
    pos_result = classify_category_aspect(positive_text)
    neg_result = classify_category_aspect(negative_text)
    
    print(f"Positive Text Score: {pos_result.sentiment_score} (Label: {pos_result.sentiment_label})")
    print(f"Negative Text Score: {neg_result.sentiment_score} (Label: {neg_result.sentiment_label})")
    
    if pos_result.sentiment_score > 0 and neg_result.sentiment_score < 0:
        print("✅ TextClassifier logic verified.")
    else:
        print("❌ TextClassifier logic FAILED.")
        return

    print("\n2. Checking Database Schema and Content...")
    from sqlalchemy.ext.asyncio import create_async_engine
    
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    
    async with engine.connect() as conn:
        # Check column existence in MV
        print("Checking mv_analysis_labels columns...")
        result = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'mv_analysis_labels' 
            AND column_name IN ('sentiment', 'sentiment_score', 'sentiment_label');
        """))
        cols = result.fetchall()
        print(f"Found columns: {cols}")
        
        # Check if we have any non-neutral data (might be empty if we haven't re-labeled data yet)
        # But since we just added columns, they are likely NULL for old data.
        # This part mostly verifies the view is querying the table.
        
        print("Checking for sentiment columns in content_labels...")
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'content_labels' 
            AND column_name IN ('sentiment_score', 'sentiment_label');
        """))
        cols = result.fetchall()
        print(f"Found base table columns: {cols}")
        
    print("\n✅ Verification script finished.")

if __name__ == "__main__":
    asyncio.run(verify())
