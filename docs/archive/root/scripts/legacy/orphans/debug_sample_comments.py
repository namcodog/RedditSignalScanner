import asyncio
from sqlalchemy import text
from app.db.session import SessionFactory
from app.services.text_classifier import classify_category_aspect, Category
from app.services.analysis.quote_extractor import QuoteExtractor

async def debug_sample_comments():
    print("Debug: Sample Comments Check")
    topic_kw = ["coffee", "machine", "espresso"] # keywords for "家用咖啡机"
    subs = ["r/coffee", "r/frugal", "r/askwomen"] # sample subs
    patterns = [f"%{k}%" for k in topic_kw]
    
    async with SessionFactory() as session:
        # 1. Check Raw Count matches
        print(f"\n1. Checking Raw Matches for {topic_kw} in {subs}...")
        sql = text("""
            SELECT body, subreddit, reddit_comment_id
            FROM comments
            WHERE lower(subreddit) = ANY(:subs)
              AND body ILIKE ANY(:patterns)
              AND LENGTH(body) > 20
            LIMIT 20
        """)
        # Note: subs in DB are r/prefixed. Input to query must match.
        # Report script was removing prefix. We fixed it to KEEP prefix.
        # Let's verify what happens with correct prefix.
        db_subs = [s.lower() for s in subs]
        
        rows = await session.execute(sql, {"subs": db_subs, "patterns": patterns})
        results = rows.fetchall()
        print(f"   Found {len(results)} potential candidates.")
        
        # 2. Simulate Filter Logic
        print("\n2. Simulating Filters on Candidates:")
        ignored_promo = 0
        ignored_other = 0
        kept = 0
        
        extractor = QuoteExtractor()
        keywords_set = set(topic_kw)
        
        for r in results:
            body = r.body
            print(f"\n--- Comment {r.reddit_comment_id} ---")
            print(f"Body: {body[:100]}...")
            
            # Promo check
            if any(x in body.lower() for x in ["promotion", "giveaway", "coupon"]):
                print("❌ Skipped: Promotion")
                ignored_promo += 1
                continue
                
            # Category check
            cls = classify_category_aspect(body)
            print(f"Category: {cls.category}, Aspect: {cls.aspect}")
            
            if cls.category == Category.OTHER:
                print("❌ Skipped: Category.OTHER")
                ignored_other += 1
                continue
                
            # Quote Score
            best_qr = None
            for sentence in extractor._iter_sentences([body]):
                qr = extractor._build_scored_quote(sentence, keywords_set, source="comment")
                if qr and (best_qr is None or qr.score > best_qr.score):
                    best_qr = qr
            
            if best_qr is None:
                 print("❌ Skipped: Quote Score None (All sentences failed)")
            else:
                 print(f"✅ KEPT! Best Sentence: '{best_qr.text[:50]}...' Score: {best_qr.score:.3f}")
                 kept += 1
                
        print(f"\nSummary: {len(results)} candidates -> {kept} kept.")
        print(f"Ignored: Promo={ignored_promo}, Other={ignored_other}")

if __name__ == "__main__":
    asyncio.run(debug_sample_comments())
