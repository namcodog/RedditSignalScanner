"""
批量添加垃圾过滤规则。
"""
import json
import sys
import os
from sqlalchemy import create_engine, text

# Fix path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.core.config import get_settings

def add_spam_rules():
    settings = get_settings()
    url = settings.database_url.replace("asyncpg", "psycopg")
    engine = create_engine(url, future=True)

    # 垃圾词列表 (Keyword, Weight)
    spam_keywords = [
        # Crypto/Scam
        ("crypto", -0.8), ("nft", -0.8), ("bitcoin", -0.8), ("token", -0.8),
        # Marketing
        ("discount", -0.5), ("giveaway", -0.5), ("promo", -0.5), ("coupon", -0.5),
        ("50% off", -0.6), ("free shipping", -0.5), ("check out my", -0.4),
        # NSFW/Spam
        ("onlyfans", -1.0), ("fansly", -1.0),
        # Traffic Exchange
        ("follow for follow", -1.0), ("like for like", -1.0)
    ]

    with engine.begin() as conn:
        # 1. 获取 global_filter_keywords 的 Concept ID
        res = conn.execute(text("SELECT id FROM semantic_concepts WHERE code = 'global_filter_keywords'"))
        concept_id = res.scalar()
        
        if not concept_id:
            print("❌ Error: Concept 'global_filter_keywords' not found!")
            return

        print(f"Found concept_id: {concept_id}")

        # 2. 批量插入
        count = 0
        for term, weight in spam_keywords:
            conn.execute(
                text("""
                    INSERT INTO semantic_rules (concept_id, term, rule_type, weight, meta)
                    VALUES (:cid, :term, 'keyword', :weight, '{"source": "scout_v1"}')
                    ON CONFLICT (concept_id, term, rule_type) 
                    DO UPDATE SET weight = EXCLUDED.weight, updated_at = NOW()
                """),
                {"cid": concept_id, "term": term, "weight": weight}
            )
            count += 1
            
        print(f"✅ Successfully added/updated {count} spam rules.")

if __name__ == "__main__":
    add_spam_rules()
