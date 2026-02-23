import sys
import os
import asyncio
import re
from collections import Counter, defaultdict
from sqlalchemy import text
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory

# Expanded Stopwords List
STOPWORDS = {
    'the', 'and', 'to', 'of', 'a', 'in', 'is', 'for', 'on', 'with', 'my', 'it', 'help', 
    'question', 'what', 'how', 'are', 'do', 'can', 'this', 'that', 'have', 'need', 'be', 
    'or', 'any', 'from', 'not', 'at', 'as', 'will', 'if', 'has', 'but', 'was', 'so', 
    'just', 'about', 'me', 'up', 'out', 'like', 'an', 'advice', 'looking', 'new', 'get',
    'good', 'best', 'vs', 'recommendation', 'recommend', 'suggestions', 'anyone', 'know',
    'please', 'would', 'should', 'one', 'use', 'using', 'make', 'doing', 'why', 'does',
    'where', 'when', 'some', 'review', 'thoughts', 'experience', 'time', 'first', 'work',
    # V1 Noise
    'you', 'your', 'actually', 'now', 'after', 'still', 'here', 'else', 'there', 'way', 
    'small', 'all', 'amp', 'more', 'very', 'much', 'want', 'did', 'had', 'been', 'who',
    'their', 'them', 'than', 'into', 'only', 'other', 'its', 'over', 'back', 'see',
    'try', 'find', 'start', 'started', 'starting', 'think', 'thinking', 'which', 'off',
    'business', 'product', 'sales', 'website', 'store', 'account', 'seller', 'shipping', 'free', # These are generic topics, keep or filter? 
    # Let's KEEP "business", "product" etc for context, but filter "actually", "now" etc.
    'really', 'got', 'too', 'well', 'don', 'didn', 'even', 'sure', 'lot', 'thing', 'things',
    'going', 'getting', 'go', 'year', 'years', 'day', 'days', 'week', 'weeks', 'month', 'months'
}

def extract_tokens(text_content):
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text_content.lower())
    return [w for w in words if w not in STOPWORDS]

async def generate_heatmap_v2():
    session = SessionFactory()
    try:
        print("--- 🔥 跨界话题热力图 V2 (Refined) ---")
        
        # 1. Select High Yield Communities (Top 40)
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
        print(f"Scanning {len(target_names)} communities...")
        
        topic_map = defaultdict(set)
        keyword_counts = Counter()
        
        for name in target_names:
            sql = f"SELECT title FROM posts_raw WHERE subreddit = '{name}' ORDER BY created_at DESC LIMIT 100"
            res = await session.execute(text(sql))
            titles = res.fetchall()
            
            for t in titles:
                tokens = extract_tokens(t[0])
                for token in tokens:
                    topic_map[token].add(name)
                    keyword_counts[token] += 1
        
        scored_topics = []
        for term, sub_set in topic_map.items():
            if len(sub_set) < 3: 
                continue
            
            count = keyword_counts[term]
            spread = len(sub_set)
            score = count * (spread) 
            
            scored_topics.append({
                'term': term,
                'score': score,
                'count': count,
                'spread': spread,
                'examples': list(sub_set)[:4]
            })
            
        scored_topics.sort(key=lambda x: x['score'], reverse=True)
        
        print(f"\n🏆 Top 30 深度跨界话题:")
        print(f"{'Topic':<20} | {'Heat':<5} | {'Spread':<2} | {'Seen In (Sample)'}")
        print("-" * 70)
        
        for item in scored_topics[:30]:
            ex_str = ", ".join(item['examples'])
            print(f"{item['term']:<20} | {item['score']:<5} | {item['spread']:<2} | {ex_str}...")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(generate_heatmap_v2())
