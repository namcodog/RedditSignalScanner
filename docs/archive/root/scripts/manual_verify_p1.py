import asyncio
import logging
import sys
from unittest.mock import AsyncMock
from pathlib import Path

# Add backend to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.incremental_crawler import IncrementalCrawler
from app.services.reddit_client import RedditPost

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

async def main():
    print("\n--- Testing Spam Filter Logic ---")
    
    # Mock dependencies
    mock_db = AsyncMock()
    mock_client = AsyncMock()
    
    crawler = IncrementalCrawler(db=mock_db, reddit_client=mock_client)
    
    # Test Case 1: Spam Post (Title)
    spam_post_1 = RedditPost(
        id="spam1", title="[placeholder missing post]", selftext="normal text",
        score=1, num_comments=0, created_utc=1000.0, subreddit="test",
        author="bot", url="", permalink=""
    )
    
    # Test Case 2: Spam Post (Body)
    spam_post_2 = RedditPost(
        id="spam2", title="Normal Title", selftext="Hello Welcome to AmazonFC rules...",
        score=1, num_comments=0, created_utc=1000.0, subreddit="test",
        author="bot", url="", permalink=""
    )
    
    # Test Case 3: Good Post
    good_post = RedditPost(
        id="good1", title="Good Title", selftext="Good content",
        score=1, num_comments=0, created_utc=1000.0, subreddit="test",
        author="user", url="", permalink=""
    )
    
    # Verify internal logic directly
    print(f"Spam 1 Detected: {crawler._is_spam_post(spam_post_1)} (Expected: True)")
    print(f"Spam 2 Detected: {crawler._is_spam_post(spam_post_2)} (Expected: True)")
    print(f"Good Post Detected: {crawler._is_spam_post(good_post)} (Expected: False)")

if __name__ == "__main__":
    asyncio.run(main())
