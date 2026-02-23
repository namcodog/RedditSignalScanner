#!/usr/bin/env python3
import asyncio
import os
import sys
import json
import yaml
import re
import aiohttp
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Path Setup
CURRENT_FILE = os.path.abspath(__file__)
SCRIPTS_DIR = os.path.dirname(CURRENT_FILE)
BACKEND_DIR = os.path.dirname(SCRIPTS_DIR)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

sys.path.append(BACKEND_DIR)
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from sqlalchemy import text
from app.db.session import SessionFactory

# ==============================================================================
# CONFIGURATION
# ==============================================================================
BATCH_SIZE = 500
CONCURRENCY = 30
MODEL_NAME = "gemini-2.5-flash-lite"
API_KEY = os.getenv("GEMINI_API_KEY")
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
CONFIG_DIR = os.path.join(BACKEND_DIR, "config")

if not API_KEY:
    print("❌ Error: GEMINI_API_KEY not found")
    sys.exit(1)

# ==============================================================================
# 1. RULEBOOK LOADER
# ==============================================================================
class RulebookLoader:
    def __init__(self):
        self.pain_dict = self._load_yaml("pain_dictionary.yaml")
        self.entity_dict = self._load_yaml("entity_dictionary.yaml")
        
    def _load_yaml(self, filename: str) -> Dict:
        path = os.path.join(CONFIG_DIR, filename)
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

# ==============================================================================
# 2. CLIENT
# ==============================================================================
class GoogleDirectClient:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session

    async def generate_json(self, prompt: str) -> Dict:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.1}
        }
        try:
            async with self.session.post(API_URL, json=payload) as response:
                if response.status != 200: return {}
                result = await response.json()
                raw = result['candidates'][0]['content']['parts'][0]['text']
                return json.loads(raw)
        except Exception:
            return {}

# ==============================================================================
# 3. CALCULATOR (POST VERSION)
# ==============================================================================
class PostScoreCalculator:
    @staticmethod
    def compute(analysis: Dict) -> Dict:
        base_score = 3.0
        
        # 1. Content Type
        ctype = analysis.get("content_type", "other")
        if ctype == "user_review": base_score += 3.0
        elif ctype == "ask_question": base_score += 1.0
        elif ctype == "news_sharing": base_score += 1.0
        elif ctype == "rant": base_score += 2.0 

        # 2. Intent
        intent = analysis.get("main_intent", "offtopic")
        if intent == "share_solution": base_score += 2.0
        elif intent == "complain": base_score += 2.0
        elif intent == "recommend_product": base_score += 1.0

        # 3. Pains
        pains = analysis.get("pain_tags", [])
        base_score += min(len(pains) * 1.5, 4.5) # Pain is king for posts

        # 4. Crossborder
        cb = analysis.get("crossborder_signals", {})
        if cb.get("mentions_shipping"): base_score += 1.0
        if cb.get("mentions_tax"): base_score += 1.0
        
        # 5. Purchase Intent
        pi_score = analysis.get("purchase_intent_score", 0.0)
        if pi_score > 0.7: base_score *= 1.2

        final_value = max(0.0, min(10.0, base_score))
        
        # Opp Score
        opp_score = (len(pains) * 0.25) + (pi_score * 0.5)
        if intent == "complain": opp_score += 0.2
        final_opp = max(0.0, min(1.0, opp_score))

        pool = "lab"
        if final_value >= 8.0: pool = "core"
        elif final_value <= 3.9: pool = "noise"

        return {
            "value_score": round(final_value, 2),
            "opportunity_score": round(final_opp, 2),
            "business_pool": pool
        }

# ==============================================================================
# 4. PIPELINE
# ==============================================================================
class PostPipeline:
    def __init__(self, http_session: aiohttp.ClientSession):
        self.rules = RulebookLoader()
        self.llm = GoogleDirectClient(http_session)
        self.calculator = PostScoreCalculator()

    async def pre_process(self, title: str, body: str) -> str:
        text_content = (title + " " + body).lower()
        hints = []
        if "shipping" in text_content or "tax" in text_content: hints.append("Check logistics")
        if "price" in text_content or "budget" in text_content: hints.append("Check price/budget")
        return "\n".join(hints)

    async def analyze(self, post: Dict) -> Dict:
        hints = await self.pre_process(post['title'], post['body'])
        prompt = f"""
        Analyze Reddit Post.
        Context: r/{post['subreddit']}
        Hints: {hints}
        Title: "{post['title']}"
        Body: "{post['body'][:2000]}"
        
        OUTPUT JSON:
        {{
          "content_type": "ask_question" | "user_review" | "news_sharing" | "discussion" | "rant" | "other",
          "main_intent": "complain" | "ask_help" | "share_solution" | "recommend_product" | "offtopic",
          "sentiment": float (-1.0 to 1.0),
          "pain_tags": ["list"],
          "aspect_tags": ["Price", "Quality", "Logistics"],
          "entities": {{ "known": [], "new": [] }},
          "crossborder_signals": {{ "mentions_shipping": bool, "mentions_tax": bool }},
          "purchase_intent_score": float (0.0-1.0),
          "opportunity_hint": "string"
        }}
        """
        return await self.llm.generate_json(prompt)

    async def save_result(self, session, post_id: int, analysis: Dict, scores: Dict):
        if not analysis: return

        # 1. Archive Old Version
        await session.execute(text("""
            UPDATE post_scores SET is_latest = FALSE 
            WHERE post_id = :pid AND is_latest = TRUE
        """), {"pid": post_id})

        # 2. Insert New Version
        await session.execute(text("""
            INSERT INTO post_scores (
                post_id, llm_version, rule_version, value_score, opportunity_score,
                business_pool, sentiment, purchase_intent_score, tags_analysis, entities_extracted
            ) VALUES (
                :pid, :llm_v, :rule_v, :val_s, :opp_s, :pool, :sent, :pi_s, :tags, :ents
            )
        """), {
            "pid": post_id,
            "llm_v": f"v1-{MODEL_NAME}-direct",
            "rule_v": "rulebook_v1",
            "val_s": scores['value_score'],
            "opp_s": scores['opportunity_score'],
            "pool": scores['business_pool'],
            "sent": analysis.get('sentiment', 0),
            "pi_s": analysis.get('purchase_intent_score', 0),
            "tags": json.dumps(analysis),
            "ents": json.dumps(analysis.get('entities', {}))
        })
        
        if scores['business_pool'] == 'core':
             await session.execute(text("UPDATE posts_raw SET business_pool='core' WHERE id=:pid"), {"pid": post_id})

    async def process_item(self, session, post):
        analysis = await self.analyze(post)
        if analysis:
            scores = self.calculator.compute(analysis)
            await self.save_result(session, post['post_id'], analysis, scores)

# ==============================================================================
# MAIN
# ==============================================================================
async def worker(worker_id: int, queue: asyncio.Queue, db_session):
    async with aiohttp.ClientSession() as http_session:
        pipeline = PostPipeline(http_session)
        while True:
            post = await queue.get()
            try:
                await pipeline.process_item(db_session, post)
            except Exception:
                pass
            finally:
                queue.task_done()

async def main():
    print("🚀 Starting Phase D: Post Refinement (Legacy Upgrade - Google Direct)...")
    async with SessionFactory() as session:
        while True:
            query = text("""
                SELECT ps.post_id, p.title, p.body, p.subreddit
                FROM post_scores ps
                JOIN posts_raw p ON ps.post_id = p.id
                WHERE ps.is_latest = TRUE
                  AND ps.llm_version = 'legacy_rule'
                LIMIT :limit
            """)
            
            result = await session.execute(query, {"limit": BATCH_SIZE})
            candidates = [dict(row._mapping) for row in result]
            
            if not candidates:
                print("💤 No more legacy posts to upgrade.")
                break

            print(f"📥 Batch: {len(candidates)} posts...")
            queue = asyncio.Queue()
            for c in candidates: queue.put_nowait(c)
            
            workers = [asyncio.create_task(worker(i, queue, session)) for i in range(CONCURRENCY)]
            await queue.join()
            for w in workers: w.cancel()
            
            await session.commit()
            print("✅ Batch committed.")

if __name__ == "__main__":
    asyncio.run(main())
