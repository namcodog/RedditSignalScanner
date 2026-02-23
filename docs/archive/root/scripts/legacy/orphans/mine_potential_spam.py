"""
深度垃圾词挖掘脚本 (The Noise Mining Algorithm)
基于统计学特征，从历史数据中识别高风险垃圾词汇。

Version: 2.1 (Enhanced Features)
Upgrades:
- Symbol Density Analysis (!!!, $$$, emojis)
- Short Link Detection
- Aggressive Domain Filtering
"""
import os
import sys
import re
import pandas as pd
from collections import Counter
from urllib.parse import urlparse
from sqlalchemy import create_engine, text

# 环境配置
sys.path.append(os.path.join(os.getcwd(), 'backend'))
# Ensure app module can be found even if current dir is not root
sys.path.append(os.path.join(os.getcwd(), '..', '..')) 

try:
    from app.core.config import get_settings
except ImportError:
    # Fallback for direct execution from scripts dir
    sys.path.append(os.getcwd())
    from app.core.config import get_settings

def mine_spam():
    print("🔍 Starting Deep Noise Mining (Last 12 Months) - Enhanced Mode...")
    
    settings = get_settings()
    url = settings.database_url.replace("asyncpg", "psycopg")
    engine = create_engine(url, future=True)
    
    # 1. 提取数据
    query = """
    SELECT title, body, url, score
    FROM posts_raw
    WHERE created_at > NOW() - INTERVAL '1 year'
      AND (score <= 0 OR is_deleted = true) 
    ORDER BY score ASC
    LIMIT 30000;
    """
    # Note: Stricter filter score <= 0 to focus on real spam
    
    try:
        print("   Loading low-quality data (Score <= 0)...")
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
    except Exception as e:
        print(f"❌ Database Error: {e}")
        return

    if df.empty:
        print("⚠️ No data found.")
        return

    print(f"✅ Loaded {len(df)} potential spam posts.")

    # -------------------------------------------------------
    # Module A: 符号密度分析 (Symbol Density)
    # -------------------------------------------------------
    print("\n🤬 [Symbol Analysis] High-Density Spam Patterns:")
    high_symbol_posts = []
    
    for txt in df['title'].fillna('') + ' ' + df['body'].fillna('') :
        if len(txt) < 10: continue
        # Count symbols like !, $, *, emoji
        symbols = len(re.findall(r'[!$*?#@💰🔥🚀]', txt))
        density = symbols / len(txt)
        if density > 0.1 or (symbols > 3 and density > 0.05):
            high_symbol_posts.append(txt[:50] + "...")
            
    print(f"   Found {len(high_symbol_posts)} posts with >10% symbol density.")
    if high_symbol_posts:
        print(f"   Sample: {high_symbol_posts[:3]}")

    # -------------------------------------------------------
    # Module B: 域名黑名单挖掘 (Domain Blacklist)
    # -------------------------------------------------------
    print("\n🌐 [Domain Analysis] Top Suspicious Domains:")
    domains = []
    whitelist = {
        'www.reddit.com', 'i.redd.it', 'v.redd.it', 'youtu.be', 'www.youtube.com', 
        'imgur.com', 'twitter.com', 'x.com', 'instagram.com', 'github.com',
        'en.wikipedia.org', 'linkedin.com', 'i.imgur.com', 'google.com'
    }
    
    # 正则匹配短链接特征
    short_link_pattern = re.compile(r'https?://(bit\.ly|t\.co|tinyurl\.com|goo\.gl)/[a-zA-Z0-9]+')
    short_links_found = 0

    for row_url in df['url'].dropna():
        u = str(row_url).strip()
        if not u.startswith('http'): continue
        
        # Check short links
        if short_link_pattern.search(u):
            short_links_found += 1

        try:
            domain = urlparse(u).netloc.lower()
            if domain.startswith('www.'): domain = domain[4:]
            if domain not in whitelist:
                domains.append(domain)
        except: pass
    
    print(f"   Found {short_links_found} short links (bit.ly, etc).")
    
    domain_counts = Counter(domains).most_common(20)
    for d, c in domain_counts:
        print(f"   - {d}: {c} hits")

    # -------------------------------------------------------
    # Module C: 垃圾短语挖掘 (Stopwords removed)
    # -------------------------------------------------------
    print("\n💬 [Phrase Analysis] Top Suspicious Phrases:")
    
    # Enhanced Stopwords
    stop_words = {
        'the', 'and', 'to', 'of', 'a', 'in', 'is', 'it', 'for', 'this', 'that', 'on', 'with', 'my', 
        'are', 'have', 'be', 'just', 'not', 'so', 'but', 'was', 'can', 'if', 'at', 'me', 'do', 
        'you', 'your', 'from', 'or', 'an', 'as', 'up', 'out', 'about', 'what', 'how', 'get', 'has', 
        'when', 'who', 'why', 'all', 'we', 'there', 'one', 'would', 'will', 'like', 'more', 'some',
        'any', 'by', 'now', 'time', 'know', 'think', 'good', 'really', 'see', 'want', 'been', 'too',
        'much', 'am', 'im', 'dont', 've', 'does', 'did', 'go', 'got', 'us', 'them', 'than', 'then',
        'also', 'into', 'even', 'back', 'only', 'new', 'no', 'other', 'very', 'make', 'because',
        'should', 'need', 'help', 'please', 'anyone', 'feel', 'looking', 'advice', 'question' # Removing "Help" signals based on previous learning
    }

    ngrams = []
    for idx, row in df.iterrows():
        # Simple clean
        txt = re.sub(r'[^a-z0-9\s]', '', (str(row['title']) + " " + str(row['body'])).lower())
        tokens = txt.split()
        if len(tokens) < 3: continue
        
        for i in range(len(tokens) - 1):
            if tokens[i] not in stop_words and tokens[i+1] not in stop_words:
                ngrams.append(f"{tokens[i]} {tokens[i+1]}")

    for phrase, count in Counter(ngrams).most_common(30):
        if count > 3:
            print(f"   - '{phrase}': {count} hits")

if __name__ == "__main__":
    mine_spam()