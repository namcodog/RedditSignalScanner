#!/usr/bin/env python3
import asyncio
import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Any

# Ensure backend path is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import async_session_factory
from app.services.llm.factory import LLMFactory

# Configuration
BATCH_SIZE = 20  # Limit API calls per run
MODEL_NAME = "google/gemini-2.5-flash-lite" # Cost-effective model

class CommentRefiner:
    def __init__(self):
        self.llm = LLMFactory.create_client(provider="openrouter", model=MODEL_NAME)
        
    async def fetch_candidates(self, session, limit: int = 20) -> List[Dict]:
        """
        Select 'Elite' candidates for AI refinement.
        Strict Criteria (to save money):
        1. Parent Post is CORE (High Value).
        2. Comment Length > 200 chars (Detailed).
        3. High Reddit Score (Popularity proxy).
        4. Not yet refined by AI.
        """
        query = text("""
            SELECT 
                c.id, 
                c.body, 
                c.subreddit, 
                c.score,
                p.title as post_title
            FROM comments c
            JOIN posts_raw p ON c.post_id = p.id
            WHERE 
                p.business_pool = 'core'          -- 1. Only Core posts
                AND length(c.body) > 200          -- 2. Only Long comments
                AND c.business_pool != 'noise'    --    No trash
                AND (c.score_source IS NULL OR c.score_source != 'ai_refiner') -- Not yet refined
            ORDER BY c.score DESC                 -- 3. Prioritize high upvotes (Top N)
            LIMIT :limit
        """)
        
        result = await session.execute(query, {"limit": limit})
        return [dict(row._mapping) for row in result]

    async def analyze_comment(self, comment: Dict) -> Dict:
        """
        Ask LLM to rate, classify, and extract entities.
        """
        prompt = f"""
        You are a Data Refiner. Analyze this Reddit comment for business value.
        
        Context:
        Subreddit: r/{comment['subreddit']}
        Post: {comment['post_title']}
        Comment: "{comment['body'][:1000]}"... (truncated)

        Task:
        1. Rate Value (0-10): Focus on actionable info (solutions, prices, detailed reviews).
        2. Classify (Label): [rant, question, experience, recommendation, noise]
        3. Extract Entities: Product names, Brands, or specific Scenarios mentioned.
        
        Output JSON:
        {{
            "score": <int>,
            "label": "<string>",
            "entities": ["<string>", "<string>"]
        }}
        """
        
        try:
            response = await self.llm.generate_json(prompt)
            return {
                "id": comment['id'],
                "new_score": response.get("score", 0),
                "label": response.get("label", "general"),
                "entities": response.get("entities", [])
            }
        except Exception as e:
            print(f"Error analyzing comment {comment['id']}: {e}")
            return None

    async def update_db(self, session, results: List[Dict]):
        """
        Write results back to DB (Comments table + Label/Entity tables).
        """
        if not results:
            return

        for res in results:
            if not res: continue
            
            # 1. Determine new pool
            new_pool = 'lab'
            if res['new_score'] >= 8:
                new_pool = 'core'
            elif res['new_score'] <= 2:
                new_pool = 'noise'
            
            # 2. Update Comments Table
            await session.execute(text("""
                UPDATE comments 
                SET 
                    value_score = :score,
                    business_pool = :pool,
                    score_source = 'ai_refiner'
                WHERE id = :id
            """), {
                "id": res['id'],
                "score": res['new_score'],
                "pool": new_pool
            })
            
            # 3. Insert Labels (content_labels)
            await session.execute(text("""
                INSERT INTO content_labels (content_type, content_id, category, confidence, source_model)
                VALUES ('comment', :id, :label, 90, :model)
            """), {
                "id": res['id'],
                "label": res['label'],
                "model": MODEL_NAME
            })
            
            # 4. Insert Entities (content_entities)
            for entity in res['entities']:
                await session.execute(text("""
                    INSERT INTO content_entities (content_type, content_id, entity, entity_type, source_model)
                    VALUES ('comment', :id, :entity, 'mixed', :model)
                """), {
                    "id": res['id'],
                    "entity": entity,
                    "model": MODEL_NAME
                })
            
            print(f"Refined {res['id']}: Score {res['new_score']} ({res['label']}) -> {new_pool}")
            
        await session.commit()

    async def run(self):
        print("Starting AI Comment Refiner (Layer 3)...")
        async with async_session_factory() as session:
            candidates = await self.fetch_candidates(session, limit=BATCH_SIZE)
            if not candidates:
                print("No elite candidates found.")
                return

            print(f"Refining {len(candidates)} elite comments...")
            tasks = [self.analyze_comment(c) for c in candidates]
            results = await asyncio.gather(*tasks)
            await self.update_db(session, results)
            print("Refinement complete.")

if __name__ == "__main__":
    runner = CommentRefiner()
    asyncio.run(runner.run())
