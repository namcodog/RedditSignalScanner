import sys
import os
import asyncio
import re
from collections import Counter, defaultdict
from sqlalchemy import text
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory

# Basic stopwords to filter out noise
STOPWORDS = {
    'the', 'and', 'to', 'of', 'a', 'in', 'is', 'for', 'on', 'with', 'my', 'it', 'help', 
    'question', 'what', 'how', 'are', 'do', 'can', 'this', 'that', 'have', 'need', 'be', 
    'or', 'any', 'from', 'not', 'at', 'as', 'will', 'if', 'has', 'but', 'was', 'so', 
    'just', 'about', 'me', 'up', 'out', 'like', 'an', 'advice', 'looking', 'new', 'get',
    'good', 'best', 'vs', 'recommendation', 'recommend', 'suggestions', 'anyone', 'know',
    'please', 'would', 'should', 'one', 'use', 'using', 'make', 'doing', 'why', 'does',
    'where', 'when', 'some', 'review', 'thoughts', 'experience', 'time', 'first', 'work'
}

def extract_tokens(text_content):
    # Simple regex for words
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text_content.lower())
    return [w for w in words if w not in STOPWORDS]

async def generate_heatmap():
    session = SessionFactory()
    try:
        print("--- 🔥 跨界话题热力图 (Cross-Community Topic Heatmap) ---")
        
        # 1. Select High Yield Communities (Top 30 by Tier 1/2)
        # Focus on Ecommerce, Home, Tools for now
        targets_sql = """
            SELECT name, vertical 
            FROM community_pool 
            WHERE is_blacklisted = false AND is_active = true 
            AND vertical IN ('Ecommerce_Business', 'Home_Lifestyle', 'Tools_EDC')
            ORDER BY tier ASC, id ASC
            LIMIT 40
        """
        res = await session.execute(text(targets_sql))
        communities = res.fetchall()
        
        target_names = [c[0] for c in communities]
        print(f"Scanning {len(target_names)} communities for cross-pollination...")
        
        # 2. Fetch Recent Titles (Limit 100 per sub to be fast)
        topic_map = defaultdict(set) # keyword -> set(communities)
        keyword_counts = Counter()   # keyword -> total_count
        
        for name in target_names:
            sql = f"SELECT title FROM posts_raw WHERE subreddit = '{name}' ORDER BY created_at DESC LIMIT 100"
            res = await session.execute(text(sql))
            titles = res.fetchall()
            
            for t in titles:
                tokens = extract_tokens(t[0])
                # Generate Bi-grams too? Simple tokens for now.
                for token in tokens:
                    topic_map[token].add(name)
                    keyword_counts[token] += 1
        
        # 3. Analyze "Cross-Boundary" Heat
        # Score = Frequency * (Unique_Communities ^ 1.5) -> Reward spread
        scored_topics = []
        for term, sub_set in topic_map.items():
            if len(sub_set) < 3: # Must appear in at least 3 distinct communities
                continue
            
            # Boost specific verticals
            count = keyword_counts[term]
            spread = len(sub_set)
            score = count * (spread) 
            
            scored_topics.append({
                'term': term,
                'score': score,
                'count': count,
                'spread': spread,
                'examples': list(sub_set)[:4] # First 4 examples
            })
            
        # 4. Sort and Display
        scored_topics.sort(key=lambda x: x['score'], reverse=True)
        
        print(f"\n🏆 Top 25 跨界话题 (Appearing in multiple communities):")
        print(f"{'Topic':<20} | {'Heat':<5} | {'Spread':<2} | {'Seen In (Sample)'}")
        print("-" * 70)
        
        for item in scored_topics[:25]:
            ex_str = ", ".join(item['examples'])
            print(f"{item['term']:<20} | {item['score']:<5} | {item['spread']:<2} | {ex_str}...")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(generate_heatmap())
