#!/usr/bin/env python3
import asyncio
import os
import sys
import json
import aiohttp
from dotenv import load_dotenv

# Path Setup
CURRENT_FILE = os.path.abspath(__file__)
SCRIPTS_DIR = os.path.dirname(CURRENT_FILE)
BACKEND_DIR = os.path.dirname(SCRIPTS_DIR)
sys.path.append(BACKEND_DIR)
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from sqlalchemy import text
from app.db.session import SessionFactory

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.5-flash-lite"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

async def test_single():
    print("🧪 Starting Single Item Diagnosis...")
    
    async with SessionFactory() as session:
        # 1. Fetch 1 Post
        query = text("""
            SELECT ps.post_id, p.title, p.body, p.subreddit
            FROM post_scores ps
            JOIN posts_raw p ON ps.post_id = p.id
            WHERE ps.is_latest = TRUE
              AND ps.llm_version = 'legacy_rule'
            LIMIT 1
        """)
        result = await session.execute(query)
        post = result.fetchone()
        
        if not post:
            print("❌ No legacy posts found.")
            return

        print(f"📄 Testing Post ID: {post.post_id}")
        print(f"📄 Title: {post.title}")

        # 2. Call API
        async with aiohttp.ClientSession() as http:
            prompt = f"""
            Analyze Reddit Post. Return valid JSON.
            Title: {post.title}
            Body: {post.body[:500]}
            
            OUTPUT JSON:
            {{
              "content_type": "ask_question",
              "main_intent": "ask_help",
              "sentiment": 0.0,
              "pain_tags": [],
              "aspect_tags": [],
              "purchase_intent_score": 0.0,
              "opportunity_hint": "test"
            }}
            """
            
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"response_mime_type": "application/json"}
            }
            
            print("📡 Sending to Google...")
            async with http.post(API_URL, json=payload) as resp:
                print(f"📡 Status Code: {resp.status}")
                if resp.status != 200:
                    err = await resp.text()
                    print(f"❌ API Failure: {err}")
                    return
                
                data = await resp.json()
                print(f"✅ API Response: {json.dumps(data, indent=2)}")
                
                try:
                    raw_text = data['candidates'][0]['content']['parts'][0]['text']
                    analysis = json.loads(raw_text)
                    print(f"✅ Parsed JSON: {analysis}")
                except Exception as e:
                    print(f"❌ JSON Parse Fail: {e}")
                    return

        # 3. Try DB Write
        print("💾 Attempting DB Write...")
        try:
            # Archive Old
            await session.execute(text("UPDATE post_scores SET is_latest=FALSE WHERE post_id=:pid"), {"pid": post.post_id})
            
            # Insert New
            await session.execute(text("""
                INSERT INTO post_scores (
                    post_id, llm_version, rule_version, value_score, opportunity_score,
                    business_pool, sentiment, purchase_intent_score, tags_analysis, entities_extracted, is_latest
                ) VALUES (
                    :pid, :llm, 'test_v1', 5.0, 0.5, 'lab', 0.0, 0.0, :tags, '[]', TRUE
                )
            """), {
                "pid": post.post_id,
                "llm": "test-run",
                "tags": json.dumps(analysis)
            })
            await session.commit()
            print("✅ DB Commit Successful.")
        except Exception as e:
            print(f"❌ DB Write Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_single())
