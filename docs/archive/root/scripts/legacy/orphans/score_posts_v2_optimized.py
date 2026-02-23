#!/usr/bin/env python3
import asyncio
import os
import sys
import json
import yaml
import re
import aiohttp
import traceback
from datetime import datetime
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
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
BATCH_SIZE = 50
CONCURRENCY = 20
MODEL_NAME = "openai/gpt-oss-120b" # Switched to OpenRouter for cost/performance
API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
API_BASE = "https://openrouter.ai/api/v1"
CONFIG_DIR = os.path.join(BACKEND_DIR, "config")
MAX_BODY_CHARS = 1000 

if not API_KEY:
    print("❌ Error: OPENROUTER_API_KEY not found")
    sys.exit(1)

# ==============================================================================
# 1. CLIENT (OpenRouter)
# ==============================================================================
class OpenRouterClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=API_BASE,
            api_key=API_KEY,
            default_headers={
                "HTTP-Referer": "https://reddit-signal-scanner.local",
                "X-Title": "Reddit Signal Scanner"
            }
        )

    async def generate_json(self, prompt: str) -> Dict:
        try:
            response = await self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1,
                timeout=120
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            # print(f"⚠️ API Error: {e}")
            return {}

# ==============================================================================
# 2. CALCULATOR (Phase D Logic)
# ==============================================================================
class PostScoreCalculator:
    @staticmethod
    def compute(analysis: Dict) -> Dict:
        base_score = 3.0
        
        # Safe Getters with Sanitization
        ctype = str(analysis.get("content_type", "other"))
        intent = str(analysis.get("main_intent", "offtopic"))
        
        pains = analysis.get("pain_tags", [])
        if not isinstance(pains, list): pains = []
        
        try: pi_score = float(analysis.get("purchase_intent_score", 0.0))
        except: pi_score = 0.0

        cb = analysis.get("crossborder_signals", {})
        if not isinstance(cb, dict): cb = {}

        if ctype == "user_review": base_score += 3.0
        elif ctype == "ask_question": base_score += 1.0
        elif ctype == "news_sharing": base_score += 1.0
        elif ctype == "rant": base_score += 2.0 

        if intent == "share_solution": base_score += 2.0
        elif intent == "complain": base_score += 2.0
        elif intent == "recommend_product": base_score += 1.0

        base_score += min(len(pains) * 1.5, 4.5)

        if cb.get("mentions_shipping"): base_score += 1.0
        if cb.get("mentions_tax"): base_score += 1.0
        
        if pi_score > 0.7: base_score *= 1.2

        final_value = max(0.0, min(10.0, base_score))
        
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
# 3. PIPELINE (The Fix: Writing to post_scores)
# ==============================================================================
class PostPipeline:
    def __init__(self):
        self.llm = OpenRouterClient()
        self.calculator = PostScoreCalculator()

    async def pre_process(self, title: str, body: str) -> str:
        text_content = (str(title) + " " + str(body)).lower()
        hints = []
        if "shipping" in text_content or "tax" in text_content: hints.append("Check logistics")
        if "price" in text_content or "budget" in text_content: hints.append("Check price/budget")
        return "\n".join(hints)

    def _safe_float(self, val):
        try: return float(val)
        except: return 0.0

    async def analyze(self, post: Dict) -> Dict:
        hints = await self.pre_process(post['title'], post['body'])
        prompt = f"""
        Analyze Reddit Post.
        Context: r/{post['subreddit']}
        Hints: {hints}
        Title: "{post['title']}"
        Body: "{post['body'][:MAX_BODY_CHARS]}"
        
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

        # Archive Old
        await session.execute(text("""
            UPDATE post_scores SET is_latest = FALSE 
            WHERE post_id = :pid AND is_latest = TRUE
        """), {"pid": post_id})

        safe_sentiment = self._safe_float(analysis.get('sentiment'))
        safe_pi = self._safe_float(analysis.get('purchase_intent_score'))
        
        clean_analysis = analysis.copy()
        if not isinstance(clean_analysis.get('pain_tags'), list): clean_analysis['pain_tags'] = []
        if not isinstance(clean_analysis.get('entities'), dict): clean_analysis['entities'] = {}

        # Insert New (Correcting the Schema v2 Target)
        await session.execute(text("""
            INSERT INTO post_scores (
                post_id, llm_version, rule_version, value_score, opportunity_score,
                business_pool, sentiment, purchase_intent_score, tags_analysis, entities_extracted, is_latest
            ) VALUES (
                :pid, :llm_v, :rule_v, :val_s, :opp_s, :pool, :sent, :pi_s, :tags, :ents, TRUE
            )
        """), {
            "pid": post_id,
            "llm_v": f"v1-{MODEL_NAME}-opt",
            "rule_v": "rulebook_v1", # Adhering to the 'rulebook_v1' standard
            "val_s": scores['value_score'],
            "opp_s": scores['opportunity_score'],
            "pool": scores['business_pool'],
            "sent": safe_sentiment,
            "pi_s": safe_pi,
            "tags": json.dumps(clean_analysis),
            "ents": json.dumps(clean_analysis.get('entities', {}))
        })
        
        # Sync to posts_raw (Legacy/Redundant but good for quick filtering)
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
async def worker(worker_id: int, queue: asyncio.Queue):
    pipeline = PostPipeline()
    while True:
        post = await queue.get()
        try:
            async with SessionFactory() as db_session:
                await pipeline.process_item(db_session, post)
                await db_session.commit()
        except Exception as e:
            # print(f"Worker Error: {e}") 
            pass
        finally:
            queue.task_done()

async def main():
    print(f"🚀 Starting Semantic Scoring (Target: OpenRouter 120B)...")
    
    while True:
        candidates = []
        async with SessionFactory() as fetch_session:
            # Fetch posts that have RAW value_score but NO post_scores entry (Fresh Wash)
            # OR fetch legacy rule_version if re-washing.
            # Strategy: Target Core/Lab posts from posts_raw that miss a 'rulebook_v1' entry in post_scores
            query = text("""
                SELECT p.id as post_id, p.title, p.body, p.subreddit
                FROM posts_raw p
                LEFT JOIN post_scores ps ON p.id = ps.post_id AND ps.rule_version = 'rulebook_v1'
                WHERE p.business_pool IN ('core', 'lab')
                  AND ps.id IS NULL
                ORDER BY p.created_at DESC
                LIMIT :limit
            """)
            result = await fetch_session.execute(query, {"limit": BATCH_SIZE})
            candidates = [dict(row._mapping) for row in result]
        
        if not candidates:
            print("💤 No more untagged posts.")
            break

        print(f"📥 Batch: {len(candidates)} posts...")
        
        queue = asyncio.Queue()
        for c in candidates: queue.put_nowait(c)
        
        workers = [asyncio.create_task(worker(i, queue)) for i in range(CONCURRENCY)]
        await queue.join()
        for w in workers: w.cancel() 
        
        print("✅ Batch processed.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
