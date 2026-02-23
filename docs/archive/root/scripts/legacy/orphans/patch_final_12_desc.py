import os
import sys
import json
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def load_env_config():
    env_path = os.path.join(os.path.dirname(__file__), '../.env')
    load_dotenv(env_path)
    url = os.getenv('DATABASE_URL')
    if url and '+asyncpg' in url:
        return url.replace('+asyncpg', '+psycopg2')
    return url

def patch_final_12():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("🩹 Patching Descriptions for the final few...\n")
    
    # 1. Identify Targets
    targets = conn.execute(text("""
        SELECT name FROM community_pool 
        WHERE is_active=true AND description_keywords = '{}'::jsonb
    """)).scalars().all()
    
    if not targets:
        print("✅ No communities missing description! All clean.")
        return

    print(f"Targets: {len(targets)}")
    print(targets)
    
    # 2. AI Knowledge Base (Manual Injection for the final few)
    # Based on the list we saw earlier: etsy, printondemand, etc.
    ai_data = {
        "r/etsy": {"description": "Etsy卖家与买家综合讨论区。", "reason": "Etsy生态的核心阵地。"},
        "r/printondemand": {"description": "按需打印(POD)商业模式讨论区。", "reason": "POD模式的垂直流量入口。"},
        "r/subreddit": {"description": "Reddit元讨论区。", "reason": "一般价值，暂留。"},
        "r/stickerstore": {"description": "贴纸卖家展示区。", "reason": "文创类细分市场。"},
        "r/lazshop_ph": {"description": "Lazada菲律宾站讨论。", "reason": "东南亚电商观察。"},
        "r/freelance": {"description": "自由职业者交流区。", "reason": "服务类电商的人群画像。"},
        "r/flipping": {"description": "二手倒卖/捡漏转卖社区。", "reason": "套利模式(Arbitrage)的底层逻辑。"},
        "r/etsytrafficjamteam": {"description": "Etsy流量互助小组。", "reason": "小卖家的推广手段观察。"},
        "r/bestaliexpressfinds": {"description": "速卖通好物推荐。", "reason": "选品灵感库。"},
        "r/logistics": {"description": "物流行业专业讨论。", "reason": "供应链趋势。"},
        "r/facebookads": {"description": "Facebook广告投放讨论。", "reason": "独立站流量核心。"},
        "r/instacartshoppers": {"description": "Instacart配送员交流。", "reason": "零工经济观察。"},
        "r/legomarket": {"description": "乐高交易市场。", "reason": "玩具品类风向标。"},
        "r/spellcasterreviews": {"description": "神秘学服务评论。", "reason": "边缘样本。"},
        "r/aliexpressbr": {"description": "速卖通巴西站。", "reason": "南美市场观察。"},
        "r/aliexpress": {"description": "速卖通综合讨论。", "reason": "跨境电商选品源头。"},
        "r/commit": {"description": "代码提交相关。", "reason": "技术边缘。"}
    }
    
    updated_count = 0
    for name in targets:
        if name in ai_data:
            desc_json = json.dumps({
                "description_zh": ai_data[name]["description"],
                "reason_zh": ai_data[name]["reason"]
            }, ensure_ascii=False)
            
            conn.execute(text("""
                UPDATE community_pool 
                SET description_keywords = :desc 
                WHERE name = :name
            """), {"desc": desc_json, "name": name})
            updated_count += 1
            
    conn.commit()
    print(f"✅ Updated {updated_count} communities.")
    
    conn.close()

if __name__ == "__main__":
    patch_final_12()
