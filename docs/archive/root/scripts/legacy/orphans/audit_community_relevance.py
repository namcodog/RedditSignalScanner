#!/usr/bin/env python3
"""
Audit active communities to identify "Employee/Noise" subreddits (e.g., r/AmazonFC).
Scoring based on content keywords:
- Employee/Work: shift, manager, hr, union, pto, upt, salary, fired, hiring
- Bot/Spam: I am a bot, automated action, removed, rule violation
- Market Value: buy, price, quality, recommend, review, deal
"""
import asyncio
from collections import defaultdict
from sqlalchemy import text
from app.db.session import SessionFactory

EMPLOYEE_KWS = {"shift", "manager", "hr", "union", "pto", "upt", "salary", "fired", "hiring", "interview", "boss", "supervisor", "warehouse"}
MARKET_KWS = {"buy", "price", "cost", "quality", "recommend", "review", "deal", "worth", "purchase", "shipping", "defective", "return"}

OUTPUT_FILE = "reports/community_relevance_audit.md"

async def audit():
    async with SessionFactory() as session:
        # Get active communities
        coms = await session.execute(text("SELECT id, name FROM community_pool WHERE is_active = true"))
        communities = coms.fetchall()
        
        print(f"Auditing {len(communities)} active communities...")
        
        results = []
        
        for cid, cname in communities:
            # Sample recent 100 posts/comments text
            # Combined text from posts and comments
            rows = await session.execute(text("""
                (SELECT title || ' ' || body as text FROM posts_raw 
                 WHERE LOWER(subreddit) = LOWER(:cname) LIMIT 50)
                UNION ALL
                (SELECT body as text FROM comments 
                 WHERE LOWER(subreddit) = LOWER(:cname) LIMIT 50)
            """), {"cname": cname})
            
            texts = [r.text.lower() for r in rows.fetchall() if r.text]
            
            total_words = 0
            emp_hits = 0
            mkt_hits = 0
            
            for t in texts:
                words = set(t.split())
                total_words += len(words)
                emp_hits += sum(1 for w in words if w in EMPLOYEE_KWS)
                mkt_hits += sum(1 for w in words if w in MARKET_KWS)
            
            # Scores (density per 1000 words)
            emp_score = (emp_hits / total_words * 1000) if total_words > 0 else 0
            mkt_score = (mkt_hits / total_words * 1000) if total_words > 0 else 0
            
            # Classification
            # High Employee Score + Low Market Score = DELETE
            status = "KEEP"
            if emp_score > 5 and emp_score > mkt_score * 2:
                status = "PURGE (Employee)"
            elif mkt_score < 2 and emp_score < 2:
                status = "REVIEW (Low Signal)"
            
            results.append({
                "name": cname,
                "emp_score": round(emp_score, 2),
                "mkt_score": round(mkt_score, 2),
                "status": status,
                "sample_size": len(texts)
            })

    # Sort by Status (Purge first), then Emp Score desc
    results.sort(key=lambda x: (x["status"] == "KEEP", -x["emp_score"]))
    
    with open(OUTPUT_FILE, "w") as f:
        f.write("# Community Relevance Audit\n\n")
        f.write("| Community | Status | Emp Score (Noise) | Mkt Score (Value) | Valid Samples |\n")
        f.write("|---|---|---|---|---|\n")
        
        for r in results:
            icon = "🟢" if r["status"] == "KEEP" else "🔴" if "PURGE" in r["status"] else "🟡"
            f.write(f"| {icon} r/{r['name']} | **{r['status']}** | {r['emp_score']} | {r['mkt_score']} | {r['sample_size']} |\n")
            
    print(f"✅ Audit complete. Check {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(audit())
