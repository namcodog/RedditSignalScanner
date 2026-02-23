
import asyncio
from app.db.session import SessionFactory
from app.services.analysis.community_ranker import compute_ranking_scores

async def debug_ranker():
    async with SessionFactory() as session:
        print("--- Debugging Ranker Scores ---")
        subs = ["r/espresso", "r/entrepreneur", "r/legomarket"]
        scores = await compute_ranking_scores(session, subs)
        print(scores)

if __name__ == "__main__":
    asyncio.run(debug_ranker())
