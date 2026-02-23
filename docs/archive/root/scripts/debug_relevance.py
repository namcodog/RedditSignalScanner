
import asyncio
from app.db.session import SessionFactory
from app.services.t1_stats import fetch_topic_relevant_communities

async def debug_relevance():
    topic = "Espresso"
    topic_tokens = {'ristretto', 'shot', 'tamping', 'group', 'head', 'basket', 'espresso', 'grinder', 'burr', 'steam', 'portafilter', 'crema', 'technique', 'wand'}
    exclusion_tokens = {'hair', 'design', 'color', 'wood', 'interior', 'furniture', 'stain', 'recipe', 'cocktail', 'finish'}
    
    async with SessionFactory() as session:
        print("--- Calling fetch_topic_relevant_communities ---")
        rel_map = await fetch_topic_relevant_communities(
            session,
            topic=topic,
            topic_tokens=list(topic_tokens),
            exclusion_tokens=list(exclusion_tokens),
            days=365,
            min_relevance_score=5
        )
        
        print(f"Total communities found: {len(rel_map)}")
        
        # Check specific communities
        targets = ["r/espresso", "r/coffee", "r/legomarket", "r/entrepreneur"]
        for t in targets:
            print(f"{t}: {rel_map.get(t, 'NOT FOUND')}")

if __name__ == "__main__":
    asyncio.run(debug_relevance())
