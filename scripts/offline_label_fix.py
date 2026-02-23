import asyncio
import os
import yaml
import json
import re
from datetime import datetime
from typing import Dict, List, Any

import asyncpg
from dotenv import load_dotenv

# 加载环境变量
load_dotenv("backend/.env")

DB_DSN = f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:{os.getenv('POSTGRES_PASSWORD', 'postgres')}@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'reddit_signal_scanner')}"
YAML_PATH = "backend/config/pain_dictionary.yaml"

class LabelEngine:
    def __init__(self, yaml_path: str):
        self.pain_patterns: Dict[str, re.Pattern] = {}
        self.intent_patterns: Dict[str, re.Pattern] = {}
        self.load_rules(yaml_path)
        
        # 补充：硬编码的意图规则 (Intent)
        self.intent_patterns['w2c'] = re.compile(r'\b(w2c|where to (buy|cop|get)|recommend|suggestion|alternative to)\b', re.IGNORECASE)
        self.intent_patterns['review'] = re.compile(r'\b(review|thoughts on|experience with)\b', re.IGNORECASE)

        # 补充：硬编码的品牌/竞品规则 (Entities)
        # 这里的列表应根据实际情况扩展，目前先覆盖报告中提到的支付相关
        brands = [
            "amazon", "shopify", "etsy", "paypal", "stripe", "wise", "payoneer", 
            "facebook", "meta", "tiktok", "google", "apple"
        ]
        self.brand_patterns = {b: re.compile(rf'\b{re.escape(b)}\b', re.IGNORECASE) for b in brands}

    def load_rules(self, path: str):
        print(f"📖 Loading rules from {path}...")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
            count = 0
            for key, val in data.items():
                # 使用 key 作为匹配词，或者尝试从 title_cn/insight 里提取（这里简化为 key匹配）
                # 实际生产中应该在 yaml 里加一个 keywords 列表。
                # 为了让脚本现在就能跑，我们做一个假设：如果帖子包含 key 本身，或者 title_cn 里的词，就算命中。
                
                # 构造一个宽松的正则：匹配 key 本身
                # 例如 key='fba', 匹配单词 fba
                pattern_str = rf"\b{re.escape(key)}\b"
                
                # 如果有 insight，也可以尝试匹配 insight 里的英文关键词（如果有的话）。
                # 鉴于你的 yaml 主要是中文 title，我们主要依靠 key 本身（通常是英文缩写如 fba, vat, moq）
                
                self.pain_patterns[key] = re.compile(pattern_str, re.IGNORECASE)
                count += 1
            print(f"✅ Loaded {count} pain rules.")
            
        except Exception as e:
            print(f"❌ Failed to load YAML: {e}")

    def analyze_text(self, text: str) -> Dict[str, Any]:
        if not text: return {}, []
        
        labels = []
        entities = []
        
        # 1. Scan Pains
        for aspect, pattern in self.pain_patterns.items():
            if pattern.search(text):
                labels.append({
                    "category": "pain",
                    "aspect": aspect,
                    "sentiment": "negative", # 默认负面
                    "confidence": 0.8
                })
                
        # 2. Scan Intents
        for aspect, pattern in self.intent_patterns.items():
            if pattern.search(text):
                labels.append({
                    "category": "intent",
                    "aspect": aspect,
                    "confidence": 0.9
                })

        # 3. Scan Entities
        for brand, pattern in self.brand_patterns.items():
            if pattern.search(text):
                entities.append({
                    "name": brand,
                    "type": "brand",
                    "count": 1
                })
                
        return labels, entities

async def run_fix():
    print(f"🔌 Connecting to DB...")
    try:
        conn = await asyncpg.connect(DB_DSN)
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    engine = LabelEngine(YAML_PATH)
    
    print("\n🚀 Starting Batch Processing...")
    
    # 每次处理 1000 条，游标遍历
    BATCH_SIZE = 1000
    offset = 0
    total_updated = 0
    
    while True:
        # 读取原始文本，只读 content_labels 为空的，或者强制重跑（这里为了演示，我们只跑空的或者旧格式的）
        # 为了彻底修复，我们建议全量扫描，覆盖旧数据
        rows = await conn.fetch(f"""
            SELECT id, title, body, content_labels 
            FROM posts_hot 
            ORDER BY id DESC
            LIMIT {BATCH_SIZE} OFFSET {offset}
        """)
        
        if not rows:
            break
            
        updates = []
        
        for row in rows:
            text = f"{row['title']} {row['body'] or ''}"
            labels, entities = engine.analyze_text(text)
            
            if labels or entities:
                updates.append((
                    json.dumps(labels), 
                    json.dumps(entities), 
                    row['id']
                ))
        
        if updates:
            # 批量更新
            await conn.executemany("""
                UPDATE posts_hot 
                SET content_labels = $1::jsonb, 
                    entities = $2::jsonb 
                WHERE id = $3
            """, updates)
            total_updated += len(updates)
            print(f"   ⚡ Processed batch {offset}-{offset+BATCH_SIZE}: Updated {len(updates)} posts.")
        else:
            print(f"   💤 Processed batch {offset}-{offset+BATCH_SIZE}: No matches found.")
            
        offset += BATCH_SIZE
        
        # 安全阀：防止无限循环（虽然有 break），或测试时只跑一部分
        # if offset > 5000: break 

    print(f"\n✅ Done. Total posts updated: {total_updated}")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(run_fix())
