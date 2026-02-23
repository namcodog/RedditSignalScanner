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

def ai_patch():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("🧠 AI Generating & Patching Descriptions for 57 Communities...\n")
    
    # The Knowledge Base
    ai_data = {
        "r/aliexpress": {"description": "全球速卖通买家与爱好者社区，分享好物与避坑指南。", "reason": "洞察海外买家对中国商品的真实评价与爆款趋势。"},
        "r/aliexpressbr": {"description": "速卖通巴西用户社区，专注巴西市场的物流与关税讨论。", "reason": "巴西是速卖通核心市场，监控该区物流痛点与热销品类。"},
        "r/amazon": {"description": "亚马逊综合讨论区，涵盖新闻、服务与通用话题。", "reason": "亚马逊平台的宏观新闻与舆情风向标。"},
        "r/amazon_influencer": {"description": "亚马逊网红/KOL交流区，讨论红人计划与带货视频。", "reason": "挖掘站内视频带货趋势与红人合作机会。"},
        "r/amazonanswers": {"description": "亚马逊问题互助区，解决订单与账户疑难杂症。", "reason": "收集用户在使用亚马逊过程中的具体痛点。"},
        "r/amazonargentina": {"description": "亚马逊阿根廷相关讨论。", "reason": "南美新兴市场的早期观察。"},
        "r/amazondspdrivers": {"description": "亚马逊DSP配送司机交流区，吐槽派送压力与路线。", "reason": "侧面反映亚马逊物流末端配送的真实状况与压力点。"},
        "r/amazonecho": {"description": "亚马逊Echo/Alexa智能设备发烧友社区。", "reason": "智能家居品类的垂直用户反馈与场景洞察。"},
        "r/amazonemployees": {"description": "亚马逊企业员工（非仓库）交流区，讨论职场环境。", "reason": "了解亚马逊内部政策变动与企业文化舆情。"},
        "r/amazonfba": {"description": "亚马逊FBA卖家核心社区，讨论选品、物流与PPC广告。", "reason": "跨境电商卖家的核心情报源，必读。"},
        "r/amazonfbaonlineretail": {"description": "FBA在线套利(OA)模式卖家讨论区。", "reason": "细分套利模式的实操技巧与利润点分析。"},
        "r/amazonfbatips": {"description": "亚马逊FBA新手技巧与指南分享。", "reason": "新手卖家的常见问题库，适合挖掘入门级痛点。"},
        "r/amazonfc": {"description": "亚马逊仓库(Fulfillment Center)员工吐槽区。", "reason": "直击物流仓库的一线状况，如爆仓、加班等信号。"},
        "r/amazonflexdrivers": {"description": "亚马逊Flex众包配送司机社区。", "reason": "了解末端配送的时效性与司机端体验。"},
        "r/amazonfresh": {"description": "亚马逊生鲜服务讨论区。", "reason": "生鲜电商的消费者体验与配送问题反馈。"},
        "r/amazonmerch": {"description": "亚马逊Merch按需打印(POD)卖家社区。", "reason": "POD模式的图案趋势与版权合规性讨论。"},
        "r/amazonprime": {"description": "亚马逊Prime会员讨论区，关注会员权益与物流。", "reason": "Prime核心用户的满意度监测与痛点挖掘。"},
        "r/amazonreviews": {"description": "亚马逊买家评论分享与吐槽。", "reason": "真实买家对产品质量的直接反馈，选品避雷针。"},
        "r/amazonsellercentral": {"description": "卖家后台(Seller Central)操作疑难问答。", "reason": "技术性操作问题的集中地，反映后台系统稳定性。"},
        "r/amazonvine": {"description": "亚马逊Vine计划测评师社区。", "reason": "了解测评师的偏好与Vine计划的最新规则。"},
        "r/amazonwtf": {"description": "亚马逊奇葩商品与离谱定价吐槽区。", "reason": "发现猎奇商品与平台数据错误的娱乐性视角。"},
        "r/bestaliexpressfinds": {"description": "速卖通好物推荐与种草清单。", "reason": "挖掘低价爆款与Dropshipping选品灵感。"},
        "r/bigseo": {"description": "专业SEO从业者社区，讨论谷歌算法与流量策略。", "reason": "独立站引流的高阶技术讨论。"},
        "r/commit": {"description": "Git/代码提交相关的技术幽默。", "reason": "技术类边缘话题，暂作观察。"},
        "r/digital_marketing": {"description": "数字营销综合讨论区，涵盖SEO、PPC、社媒。", "reason": "跨境电商流量获取的宏观趋势与策略库。"},
        "r/dropshipping": {"description": "一件代发(Dropshipping)核心社区，讨论选品与建站。", "reason": "Dropshipping模式的风向标，新手与老手聚集地。"},
        "r/dropshipping_guide": {"description": "一件代发入门教程与资源分享。", "reason": "新手卖家的学习路径与痛点分析。"},
        "r/dropshippingtips": {"description": "一件代发技巧分享（含部分广告）。", "reason": "筛选有价值的实操技巧，警惕营销内容。"},
        "r/ecommercemarketing": {"description": "电商营销策略专区，专注转化率优化(CRO)与广告。", "reason": "提升店铺销量的具体战术讨论。"},
        "r/ecommerceseo": {"description": "电商垂直领域的SEO优化讨论。", "reason": "针对店铺排名的SEO技术细节。"},
        "r/etsytrafficjamteam": {"description": "Etsy卖家互助与流量提升小组。", "reason": "观察Etsy小卖家的生存状态与抱团行为。"},
        "r/facebookads": {"description": "Facebook广告投放专家社区，讨论ROAS与素材。", "reason": "独立站流量核心，监控FB广告政策与投放技巧。"},
        "r/fascamazon": {"description": "亚马逊员工综合讨论区。", "reason": "内部视角的补充。"},
        "r/fuckamazon": {"description": "反亚马逊垄断与劳工权益抗议区。", "reason": "负面舆情与品牌风险监控。"},
        "r/instacartshoppers": {"description": "Instacart代购员社区。", "reason": "零工经济与即时配送行业的参照系。"},
        "r/lazshop_ph": {"description": "Lazada菲律宾站相关讨论。", "reason": "东南亚市场（菲律宾）的电商观察。"},
        "r/legomarket": {"description": "乐高积木二级市场交易与估价。", "reason": "玩具品类的二级市场溢价与收藏趋势。"},
        "r/logistics": {"description": "全球物流与供应链行业讨论。", "reason": "海运、空运价格趋势与供应链中断预警。"},
        "r/peopleofwalmart": {"description": "沃尔玛超市奇闻趣事分享。", "reason": "美国下沉市场消费者的生活百态观察。"},
        "r/sellingonamazonfba": {"description": "亚马逊FBA销售技巧交流。", "reason": "FBA业务的补充讨论区。"},
        "r/seo_marketing_offers": {"description": "SEO与营销工具优惠信息分享。", "reason": "挖掘营销SaaS工具的折扣与新产品。"},
        "r/shopifyappdev": {"description": "Shopify应用开发者社区。", "reason": "Shopify生态系统的技术底层与API变动。"},
        "r/shopifydev": {"description": "Shopify主题与店铺装修开发者交流。", "reason": "Liquid代码修改与店铺定制化技术。"},
        "r/shopifyecommerce": {"description": "Shopify电商运营综合讨论。", "reason": "Shopify卖家的日常运营话题。"},
        "r/shopifyseo": {"description": "Shopify店铺SEO优化专区。", "reason": "针对Shopify架构的SEO特殊技巧。"},
        "r/shopifywebsites": {"description": "Shopify店铺展示与互评区。", "reason": "观察新店铺的设计风格与品类趋势。"},
        "r/spellcasterreviews": {"description": "神秘学服务（通灵/法术）评论（非常规电商）。", "reason": "非常规服务类电商的特殊样本，或需剔除。"},
        "r/stickerstore": {"description": "贴纸与手账周边卖家展示区。", "reason": "文创类小商品的细分市场观察。"},
        "r/subreddit": {"description": "Reddit社区导航与推荐。", "reason": "元数据讨论，价值较低。"},
        "r/techseo": {"description": "技术性SEO深水区，讨论爬虫、索引与架构。", "reason": "高阶SEO技术趋势。"},
        "r/tiktokshop": {"description": "TikTok Shop卖家与买家交流区。", "reason": "新兴兴趣电商平台的核心阵地，趋势必看。"},
        "r/tiktokshopsellersclub": {"description": "TikTok小店卖家俱乐部。", "reason": "TK卖家的抱团取暖与政策交流。"},
        "r/walmart": {"description": "沃尔玛超市综合讨论区（顾客与员工）。", "reason": "沃尔玛生态的宏观舆情。"},
        "r/walmart_rx": {"description": "沃尔玛药房员工交流。", "reason": "药房零售的细分观察。"},
        "r/walmartcanada": {"description": "沃尔玛加拿大分部讨论。", "reason": "加拿大零售市场的区域观察。"},
        "r/walmartemployees": {"description": "沃尔玛员工职场吐槽区。", "reason": "零售业一线用工环境的晴雨表。"},
        "r/walmartsellers": {"description": "沃尔玛第三方卖家(Marketplace)社区。", "reason": "沃尔玛电商平台的卖家生态与痛点。"}
    }
    
    updated_count = 0
    
    for name, data in ai_data.items():
        # Construct the JSONB object: {"description": "...", "reason": "..."}
        desc_json = json.dumps({
            "description_zh": data["description"],
            "reason_zh": data["reason"]
        }, ensure_ascii=False)
        
        res = conn.execute(text("""
            UPDATE community_pool 
            SET description_keywords = :desc
            WHERE name = :name
        """), {"desc": desc_json, "name": name})
        
        if res.rowcount > 0:
            updated_count += 1
            
    conn.commit()
    print(f"✅ Successfully patched {updated_count} communities with AI knowledge.")
    
    conn.close()

if __name__ == "__main__":
    ai_patch()
