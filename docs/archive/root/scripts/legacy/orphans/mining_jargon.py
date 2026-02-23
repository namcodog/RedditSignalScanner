#!/usr/bin/env python3
"""
Data Mining Script: Extract unknown high-frequency jargon from the entire database.
Strategy: Streaming SQL -> N-gram Counting -> Filtering Known Terms -> CSV Output.
"""
import asyncio
import csv
import logging
import re
import sys
from collections import Counter
from pathlib import Path

# Ensure backend is in path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from sklearn.feature_extraction.text import CountVectorizer
from app.db.session import SessionFactory

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Parameters
BATCH_SIZE = 10000
MIN_FREQUENCY = 50
NGRAM_RANGE = (2, 3)  # Focus on phrases like "shipping cost", "customer service"
OUTPUT_FILE = Path("backend/reports/jargon_candidates.csv")

# Stopwords (Basic English + Common Reddit Noise)
STOPWORDS = {
    "the", "and", "to", "of", "a", "in", "is", "that", "for", "it", "you", "on", "this", "with", 
    "be", "are", "not", "have", "as", "but", "what", "if", "can", "do", "my", "your", "so", "or",
    "at", "just", "like", "all", "from", "they", "me", "about", "get", "an", "out", "would", "up",
    "one", "will", "there", "don", "no", "really", "when", "some", "good", "time", "think", "know",
    "go", "see", "people", "make", "how", "them", "who", "by", "more", "much", "been", "was", "has",
    "thanks", "please", "hello", "anyone", "guys", "removed", "deleted", "post", "comment"
}

async def fetch_known_terms(session) -> set[str]:
    """Load existing terms from semantic_terms table to avoid rediscovering the wheel."""
    logger.info("🧠 Loading known semantic terms...")
    result = await session.execute(text("SELECT canonical FROM semantic_terms"))
    known = {row[0].lower() for row in result.fetchall()}
    logger.info(f"✅ Loaded {len(known)} known terms.")
    return known

def clean_text(text: str) -> str:
    """Basic cleaning: remove URLs, user mentions, special chars."""
    text = re.sub(r"http\S+", "", text)  # URLs
    text = re.sub(r"u/\S+", "", text)    # Reddit users
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text) # Keep only alphanumeric
    return text.lower()

async def mine_jargon():
    async with SessionFactory() as session:
        known_terms = await fetch_known_terms(session)
        
        logger.info("⛏️  Starting full-database scan (Streaming)...")
        
        # Global counter for n-grams
        global_counter = Counter()
        
        # Query comments
        # We use server-side cursor implicitly by fetching in chunks if using stream, 
        # but here we use LIMIT/OFFSET for simplicity or just fetch all ID first then batch.
        # Actually, AsyncSession.stream() is better.
        
        sql = text("SELECT body FROM comments ORDER BY id")
        result = await session.stream(sql)
        
        batch_texts = []
        total_processed = 0
        
        async for row in result:
            cleaned = clean_text(row.body)
            if len(cleaned) > 10: # Skip too short
                batch_texts.append(cleaned)
            
            if len(batch_texts) >= BATCH_SIZE:
                _process_batch(batch_texts, global_counter)
                total_processed += len(batch_texts)
                logger.info(f"🔄 Processed {total_processed} comments...")
                batch_texts = []
        
        # Process remaining
        if batch_texts:
            _process_batch(batch_texts, global_counter)
            total_processed += len(batch_texts)
        
        logger.info(f"✅ Scan complete. Processed {total_processed} comments.")
        logger.info(f"📊 Total unique phrases found: {len(global_counter)}")
        
        _export_results(global_counter, known_terms)

def _process_batch(texts: list[str], counter: Counter):
    """Extract n-grams from a batch and update the global counter."""
    try:
        vectorizer = CountVectorizer(
            ngram_range=NGRAM_RANGE, 
            stop_words=list(STOPWORDS), 
            min_df=1, # We filter later globally
            max_features=None
        )
        dtm = vectorizer.fit_transform(texts)
        counts = dtm.sum(axis=0).A1
        vocab = vectorizer.get_feature_names_out()
        
        # Update global counter
        for word, count in zip(vocab, counts):
            counter[word] += count
    except ValueError:
        # Raised if empty vocabulary (e.g. only stopwords)
        pass

def _export_results(counter: Counter, known_terms: set[str]):
    logger.info("💾 Exporting candidates...")
    
    # Filter
    candidates = []
    for phrase, count in counter.most_common(5000): # Check top 5000
        if count < MIN_FREQUENCY:
            break
        
        # Skip if contained in known terms (simple substring check)
        # or if known term is in phrase (e.g. "amazon shipping" if "amazon" is known)
        # Actually, we want to keep "amazon shipping" even if "amazon" is known, 
        # because it's a specific concept.
        # So we only skip if the EXACT phrase is known.
        if phrase in known_terms:
            continue
            
        candidates.append((phrase, count))
    
    # Write CSV
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["phrase", "frequency", "is_known"])
        for p, c in candidates:
            writer.writerow([p, c, "False"])
            
    logger.info(f"💎 Saved top {len(candidates)} candidates to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(mine_jargon())
