
import asyncio
import sys
import argparse
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Ensure backend is in pythonpath
sys.path.append(str(Path.cwd()))

from backend.app.core.config import settings
from backend.app.db.session import SessionFactory
from backend.app.services.reddit_client import RedditAPIClient

# Commercial intent keywords (English)
COMMERCIAL_REGEX = re.compile(
    r"\b(buy|bought|buying|price|cost|worth|recommend|suggestion|review|deal|budget|looking for|vs|versus|cheap|expensive|purchase|store|shop)\b",
    re.IGNORECASE
)

async def ensure_candidate(session: AsyncSession, name: str, vertical: str | None):
    """Ensure community exists in pool as 'candidate'."""
    # Check existence
    row = await session.execute(
        text("SELECT status, vertical FROM community_pool WHERE name = :name"),
        {"name": name}
    )
    existing = row.mappings().first()
    
    if existing:
        print(f"ℹ️  Community '{name}' exists. Status: {existing['status']}, Vertical: {existing['vertical']}")
        if vertical and existing['vertical'] != vertical:
            print(f"   Updating vertical to '{vertical}'...")
            await session.execute(
                text("UPDATE community_pool SET vertical = :v WHERE name = :n"),
                {"v": vertical, "n": name}
            )
            await session.commit()
    else:
        print(f"🆕 Registering new candidate '{name}'...")
        if not vertical:
            print("⚠️  Warning: No vertical provided for new community. Defaulting to 'Home_Lifestyle'.")
            vertical = "Home_Lifestyle"
            
        await session.execute(
            text("""
                INSERT INTO community_pool (name, status, vertical, categories, is_active, priority)
                VALUES (:n, 'candidate', :v, :c::jsonb, true, 'medium')
            """),
            {"n": name, "v": vertical, "c": f'["{vertical}"]'}
        )
        await session.commit()

async def fetch_sample(client: RedditAPIClient, subreddit: str) -> list[dict]:
    """Fetch a sample of posts (New + Top Month)."""
    print(f"📡 Fetching sample from r/{subreddit}...")
    
    # 1. Fetch New (Activity Velocity)
    print("   Fetching recent posts...")
    new_posts, _ = await client.fetch_subreddit_posts(subreddit, limit=50, sort="new")
    
    # 2. Fetch Top (Content Quality ceiling)
    print("   Fetching top posts (month)...")
    top_posts, _ = await client.fetch_subreddit_posts(subreddit, limit=50, sort="top", time_filter="month")
    
    # Merge and dedupe
    seen = set()
    merged = []
    for p in new_posts + top_posts:
        if p.id not in seen:
            merged.append(p)
            seen.add(p.id)
            
    print(f"✅ Fetched {len(merged)} unique posts.")
    return merged

def analyze_sample(posts: list[dict]) -> dict:
    """Calculate metrics from sample."""
    if not posts:
        return {}
        
    total = len(posts)
    
    # 1. Spam/Dead
    removed_count = sum(1 for p in posts if p.selftext in ('[removed]', '[deleted]'))
    clean_posts = [p for p in posts if p.selftext not in ('[removed]', '[deleted]')]
    clean_total = len(clean_posts)
    
    if clean_total == 0:
        return {"spam_ratio": 1.0, "clean_count": 0}

    # 2. Engagement
    comments = [p.num_comments for p in clean_posts]
    scores = [p.score for p in clean_posts]
    avg_comments = mean(comments) if comments else 0
    avg_score = mean(scores) if scores else 0
    
    # 3. Velocity (Posts per day based on Newest - Oldest in sample)
    timestamps = sorted([p.created_utc for p in clean_posts])
    if len(timestamps) > 1:
        span_seconds = timestamps[-1] - timestamps[0]
        days = span_seconds / 86400
        # If span is too short (< 1 day), use 1 day to avoid division by zero or huge numbers
        # But for 'New' sort, dense timestamps mean high velocity.
        # Let's estimate strictly from the 'New' portion if possible, but here we mixed.
        # Simplification: Just span.
        posts_per_day = (len(clean_posts) / days) if days > 0.1 else len(clean_posts)
    else:
        posts_per_day = 0
        
    # 4. Commercial Signal
    comm_hits = 0
    for p in clean_posts:
        text = f"{p.title} {p.selftext}"
        if COMMERCIAL_REGEX.search(text):
            comm_hits += 1
            
    return {
        "total_fetched": total,
        "clean_count": clean_total,
        "spam_ratio": removed_count / total,
        "posts_per_day": round(posts_per_day, 1),
        "avg_comments": round(avg_comments, 1),
        "avg_score": round(avg_score, 1),
        "commercial_ratio": round(comm_hits / clean_total, 2),
    }

def recommend_status(metrics: dict) -> tuple[str, str]:
    """Return (Status, Reason)."""
    if not metrics or metrics.get("clean_count", 0) == 0:
        return "banned", "Dead or 100% Spam"
        
    ppd = metrics["posts_per_day"]
    comm = metrics["commercial_ratio"]
    avg_c = metrics["avg_comments"]
    spam = metrics["spam_ratio"]
    
    if spam > 0.5:
        return "paused", f"Too much spam ({spam:.0%})"
        
    # Active Criteria: High signal OR (High volume + decent signal)
    if (comm >= 0.20 and avg_c >= 3) or (ppd >= 5 and comm >= 0.1):
        return "active", "High Signal/Volume"
        
    # Lab Criteria: Some signal or volume
    if comm >= 0.05 or ppd >= 1:
        return "lab", "Potential (Moderate)"
        
    return "paused", "Low Signal & Volume"

async def main():
    parser = argparse.ArgumentParser(description="Audit a subreddit for inclusion.")
    parser.add_argument("subreddit", help="Name of the subreddit (e.g. r/startups)")
    parser.add_argument("--vertical", help="Vertical tag (e.g. Ecommerce_Business)", default=None)
    
    args = parser.parse_args()
    sub_name = args.subreddit
    if sub_name.startswith("r/"):
        sub_name = sub_name[2:]
        
    print(f"🔎 Auditing r/{sub_name}...")
    
    async with SessionFactory() as session:
        await ensure_candidate(session, f"r/{sub_name}", args.vertical)
        
    async with RedditAPIClient(
        settings.reddit_client_id,
        settings.reddit_client_secret,
        settings.reddit_user_agent
    ) as client:
        posts = await fetch_sample(client, sub_name)
        
    metrics = analyze_sample(posts)
    
    print("\n📊 Health Report:")
    print("-" * 30)
    for k, v in metrics.items():
        print(f"  {k:<20}: {v}")
    print("-" * 30)
    
    status, reason = recommend_status(metrics)
    icon = {"active": "🌟", "lab": "🧪", "paused": "❄️", "banned": "💀"}.get(status, "❓")
    
    print(f"\n🤖 David's Verdict: {icon} {status.upper()}")
    print(f"   Reason: {reason}")
    print(f"\n👉 To apply: UPDATE community_pool SET status = '{status}' WHERE name = 'r/{sub_name}';")

if __name__ == "__main__":
    asyncio.run(main())
