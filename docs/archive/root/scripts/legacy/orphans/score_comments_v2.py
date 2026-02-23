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

# Ensure backend path is in sys.path
sys.path.append(BACKEND_DIR)

# Load Env explicitly
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from sqlalchemy import text
from app.db.session import SessionFactory

# ==============================================================================
# CONFIGURATION & CONSTANTS
# ==============================================================================
BATCH_SIZE = 500 # Larger batch for full run
CONCURRENCY = 30 # High concurrency
MODEL_NAME = "gemini-2.5-flash-lite"
API_KEY = os.getenv("GEMINI_API_KEY")
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
CONFIG_DIR = os.path.join(BACKEND_DIR, "config")

if not API_KEY:
    print("❌ Error: GEMINI_API_KEY not found in .env")
    sys.exit(1)

# ==============================================================================
# 1. RULEBOOK LOADER
# ==============================================================================
class RulebookLoader:
    def __init__(self):
        self.pain_dict = self._load_yaml("pain_dictionary.yaml")
        self.entity_dict = self._load_yaml("entity_dictionary.yaml")
        self.scoring_rules = self._load_yaml("scoring_rules.yaml")
        
    def _load_yaml(self, filename: str) -> Dict:
        path = os.path.join(CONFIG_DIR, filename)
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"⚠️ Warning: Could not load {filename}: {e}")
            return {}

# ==============================================================================
# 2. GOOGLE DIRECT CLIENT
# ==============================================================================
class GoogleDirectClient:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session

    async def generate_json(self, prompt: str) -> Dict:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1
            }
        }
        
        try:
            async with self.session.post(API_URL, json=payload) as response:
                if response.status != 200:
                    # err_text = await response.text() 
                    return {}
                
                result = await response.json()
                try:
                    raw_text = result['candidates'][0]['content']['parts'][0]['text']
                    return json.loads(raw_text)
                except (KeyError, IndexError, json.JSONDecodeError):
                    return {}
        except Exception:
            return {}

# ==============================================================================
# 3. CALCULATOR
# ==============================================================================
class ScoreCalculator:
    @staticmethod
    def compute(analysis: Dict) -> Dict:
        base_score = 3.0
        
        actor = analysis.get("actor_type", "other")
        if actor == "buyer_review": base_score += 2.0
        elif actor == "buyer_ask": base_score += 1.0
        elif actor == "seller_operator": base_score -= 1.0
        elif actor == "expert_sharing": base_score += 2.0

        intent = analysis.get("main_intent", "offtopic")
        if intent == "share_solution": base_score += 3.0
        elif intent == "complain": base_score += 2.0 
        elif intent == "recommend_product": base_score += 1.0
        elif intent == "offtopic": base_score -= 2.0

        pains = analysis.get("pain_tags", [])
        base_score += min(len(pains) * 1.0, 3.0)

        cb = analysis.get("crossborder_signals", {})
        if cb.get("mentions_shipping"): base_score += 1.0
        if cb.get("mentions_tax"): base_score += 1.0
        
        pi_score = analysis.get("purchase_intent_score", 0.0)
        if pi_score > 0.7:
            base_score = base_score * 1.2

        final_value = max(0.0, min(10.0, base_score))
        
        opp_score = (len(pains) * 0.2) + (pi_score * 0.5)
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
# 4. PIPELINE WORKER
# ==============================================================================
class CommentPipeline:
    def __init__(self, http_session: aiohttp.ClientSession):
        self.rules = RulebookLoader()
        self.llm = GoogleDirectClient(http_session)
        self.calculator = ScoreCalculator()

    async def pre_process(self, comment_body: str) -> str:
        hints = []
        if any(k in comment_body.lower() for k in ["shipping", "customs", "tax", "duty"]):
            hints.append("Possibility of Crossborder/Logistics issues")
        if any(k in comment_body.lower() for k in ["price", "cost", "budget", "expensive"]):
            hints.append("Pricing/Budget aspect mentioned")
        return "\n".join(hints)

    async def analyze(self, comment: Dict) -> Dict:
        hints = await self.pre_process(comment['body'])
        prompt = f"""
        Analyze this Reddit comment for Market Intelligence.
        CONTEXT: Subreddit: r/{comment['subreddit']} Post: {comment['post_title']} Hints: {hints}
        COMMENT: "{comment['body'][:1500]}"...
        OUTPUT JSON (Strictly follow this schema):
        {{
          "actor_type": "buyer_ask" | "buyer_review" | "seller_operator" | "expert_sharing" | "other",
          "main_intent": "complain" | "ask_help" | "share_solution" | "recommend_product" | "offtopic",
          "sentiment": float (-1.0 to 1.0),
          "pain_tags": ["list", "of", "pains"],
          "aspect_tags": ["Price", "Quality", "Shipping", "Service"],
          "entities": {{ "known": [], "new": [] }},
          "crossborder_signals": {{ "mentions_shipping": bool, "mentions_tax": bool, "region_inference": "string|null" }},
          "purchase_intent_score": float (0.0 to 1.0),
          "opportunity_hint": "One sentence summary"
        }}
        """
        return await self.llm.generate_json(prompt)

    async def save_result(self, session, comment_id: int, analysis: Dict, scores: Dict):
        if not analysis: return 

        await session.execute(text("""
            INSERT INTO comment_scores (
                comment_id, llm_version, rule_version, value_score, opportunity_score, 
                business_pool, sentiment, purchase_intent_score, tags_analysis, entities_extracted
            ) VALUES (
                :cid, :llm_v, :rule_v, :val_s, :opp_s, :pool, :sent, :pi_s, :tags, :ents
            )
        """), {
            "cid": comment_id,
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
            await session.execute(text("""
                UPDATE comments SET value_score = :val, business_pool = 'core', expires_at = NULL 
                WHERE id = :cid
            """), {"cid": comment_id, "val": scores['value_score']})
        
        # Reduced logging for speed
        # print(f"✅ {comment_id}: {scores['value_score']}")

    async def process_item(self, session, comment):
        analysis = await self.analyze(comment)
        if analysis:
            scores = self.calculator.compute(analysis)
            await self.save_result(session, comment['id'], analysis, scores)

# ==============================================================================
# MAIN RUNNER
# ==============================================================================
async def worker(worker_id: int, queue: asyncio.Queue, db_session):
    async with aiohttp.ClientSession() as http_session:
        pipeline = CommentPipeline(http_session)
        while True:
            comment = await queue.get()
            try:
                await pipeline.process_item(db_session, comment)
            except Exception:
                pass
            finally:
                queue.task_done()

async def main():
    print("🚀 Starting Phase C: Google Direct Pipeline (FULL RUN)...")
    
    async with SessionFactory() as session:
        while True:
            # Fetch Batch - CORRECTED SYNTAX
            query = text("""
                SELECT c.id, c.body, c.subreddit, p.title as post_title
                FROM comments c
                JOIN posts_raw p ON c.post_id = p.id
                LEFT JOIN comment_scores cs ON c.id = cs.comment_id
                WHERE p.business_pool = 'core'
                  AND length(c.body) > 200
                  AND c.business_pool != 'noise'
                  AND cs.id IS NULL
                LIMIT :limit
            """)
            
            # Correctly pass parameters to execute
            result = await session.execute(query, {"limit": BATCH_SIZE})
            candidates = [dict(row._mapping) for row in result]
            
            if not candidates:
                print("💤 No more candidates found. Job Done.")
                break

            print(f"📥 Loading batch of {len(candidates)} items...")
            
            queue = asyncio.Queue()
            for c in candidates:
                queue.put_nowait(c)
                
            workers = [asyncio.create_task(worker(i, queue, session)) for i in range(CONCURRENCY)]
            await queue.join()
            
            for w in workers:
                w.cancel()
            
            await session.commit()
            print(f"✅ Batch committed. Loop continuing...")

if __name__ == "__main__":
    asyncio.run(main())
