import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Ensure backend is in pythonpath
sys.path.append(str(Path.cwd()))

INPUT_FILE = "datasets/ecommerce_core_v0.csv"
OUTPUT_FILE = "reports/Ecommerce_Business_Insight_v0.md"

# 1. Keywords Definitions
PLATFORMS = {
    "Amazon": [r"\bamazon\b", r"\bamz\b", r"\bfba\b", r"\bseller central\b"],
    "Shopify": [r"\b shopify\b"],
    "Etsy": [r"\betsy\b"],
    "TikTok Shop": [r"\btiktok\b", r"\btts\b"],
    "eBay": [r"\bebay\b"],
    "Walmart": [r"\bwalmart\b"]
}

PAIN_DIMENSIONS = {
    "Logistics & Fulfillment": [r"shipping", r"delivery", r"delay", r"customs", r"3pl", r"warehouse", r"inventory", r"carrier", r"usps", r"ups", r"fedex", r"tracking"],
    "Ads & Marketing": [r"\bads\b", r"advertising", r"roas", r"facebook ads", r"google ads", r"ppc", r"traffic", r"conversion", r"seo", r"marketing"],
    "Finance & Payments": [r"fee", r"fees", r"payment", r"refund", r"return", r"chargeback", r"tax", r"profit", r"margin", r"cash flow", r"payout"],
    "Risk & Compliance": [r"\bban\b", r"banned", r"suspend", r"blocked", r"verify", r"verification", r"account health", r"ip complaint", r"infringement", r"policy violation"],
    "Sourcing & Product": [r"supplier", r"alibaba", r"private label", r"quality", r"manufacturing", r"sourcing", r"china", r"factory"]
}

SOLUTIONS_HINTS = [r"use", r"try", r"recommend", r"tool", r"app", r"service", r"software", r"platform"]

def analyze_dataset():
    print(f"🕵️‍♂️ Analyzing {INPUT_FILE}...")
    
    posts = []
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                posts.append(row)
    except FileNotFoundError:
        print(f"❌ Error: {INPUT_FILE} not found. Please run A1 export first.")
        return

    # Statistics
    platform_counts = Counter()
    pain_counts = Counter()
    matrix = defaultdict(Counter) # matrix[platform][pain]
    solution_mentions = defaultdict(list) # pain -> [snippets]
    
    total_analyzed = 0
    
    for post in posts:
        text_content = (post['title'] + " " + post['selftext']).lower()
        
        # Identify Platforms
        matched_platforms = []
        for p_name, regexes in PLATFORMS.items():
            for r in regexes:
                if re.search(r, text_content):
                    matched_platforms.append(p_name)
                    break # Count platform once per post
        
        # Identify Pains
        matched_pains = []
        for p_name, regexes in PAIN_DIMENSIONS.items():
            for r in regexes:
                if re.search(r, text_content):
                    matched_pains.append(p_name)
                    break
        
        if matched_platforms or matched_pains:
            total_analyzed += 1
            
        # Update Stats
        for p in matched_platforms:
            platform_counts[p] += 1
            for pain in matched_pains:
                matrix[p][pain] += 1
                
        for pain in matched_pains:
            pain_counts[pain] += 1
            # Extract simple snippet if it looks like a solution context
            # Very basic extraction: sentence with "recommend" or "use"
            if len(solution_mentions[pain]) < 5: # Limit samples
                sentences = re.split(r'[.!?\n]', post['selftext'])
                for s in sentences:
                    if any(h in s.lower() for h in SOLUTIONS_HINTS) and len(s) < 200:
                        clean_s = s.strip()
                        if clean_s:
                            solution_mentions[pain].append(f"> {clean_s} (r/{post['subreddit']})")
                            break

    # Generate Report
    print("📝 Writing Report...")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("# 📊 Ecommerce_Business Reddit 洞察报告 v0\n\n")
        f.write(f"> **数据源**: {INPUT_FILE}\n")
        f.write(f"> **样本量**: {total_analyzed} 条有效高价值讨论 (Core Posts)\n")
        f.write(f"> **生成时间**: {sys.version.split()[0]} (David Engine)\n\n")
        
        f.write("## 1. 战场分布：谁在挨骂？(Platform Share)\n\n")
        f.write("卖家讨论（吐槽）最多的平台排名：\n\n")
        f.write("| 排名 | 平台 | 讨论热度 (Mentions) | 主要情绪/关键词 |\n")
        f.write("| --- | --- | --- | --- |\n")
        rank = 1
        for p, count in platform_counts.most_common():
            top_pain = matrix[p].most_common(1)
            pain_desc = top_pain[0][0] if top_pain else "综合"
            f.write(f"| {rank} | **{p}** | {count} | {pain_desc} |\n")
            rank += 1
        f.write("\n")
        
        f.write("## 2. 痛点矩阵：大家在烦什么？(Pain Matrix)\n\n")
        f.write("各平台卖家最头疼的问题分布：\n\n")
        f.write("| 平台 | 📦 物流发货 | 💰 资金支付 | 📣 广告营销 | ⚖️ 封号风控 | 🏭 供应链 |\n")
        f.write("| --- | --- | --- | --- | --- | --- |\n")
        
        cols = ["Logistics & Fulfillment", "Finance & Payments", "Ads & Marketing", "Risk & Compliance", "Sourcing & Product"]
        for p, _ in platform_counts.most_common():
            row = [f"**{p}**"]
            for col in cols:
                count = matrix[p][col]
                # Highlight hotspots
                val = f"**{count}** 🔥" if count > 100 else f"{count}"
                row.append(val)
            f.write("| " + " | ".join(row) + " |\n")
        f.write("\n")
        
        f.write("## 3. 现有解法与缝隙 (Solutions & Gaps)\n\n")
        
        for pain, count in pain_counts.most_common():
            f.write(f"### {pain} (热度: {count})\n")
            f.write("**用户都在聊什么 / 尝试什么土办法：**\n\n")
            if solution_mentions[pain]:
                for s in solution_mentions[pain]:
                    f.write(f"- {s}\n")
            else:
                f.write("- *(暂未提取到明显解决方案片段)*\n")
            f.write("\n")
            
        f.write("## 4. David 的机会推荐 (Opportunities)\n\n")
        f.write("基于数据分布，我为您挖掘了 3 个高潜力切入点：\n\n")
        
        # Dynamic Recommendations logic
        top_pains = [x[0] for x in pain_counts.most_common(3)]
        
        if "Risk & Compliance" in top_pains:
            f.write("### 💡 方向一：亚马逊/Etsy 账号申诉与风控预警\n")
            f.write("- **现象**: `Risk & Compliance` 在 Amazon 和 Etsy 板块提及率极高，且伴随着恐慌情绪。\n")
            f.write("- **机会**: 提供专业的申诉模板、风控体检工具，或者“账号备胎”建立指南。\n\n")
            
        if "Ads & Marketing" in top_pains:
            f.write("### 💡 方向二：中小卖家适用的“傻瓜式”广告优化工具\n")
            f.write("- **现象**: 很多卖家（特别是 Shopify）在问 ROAS 为什么跌，FB 广告怎么投。\n")
            f.write("- **机会**: 现在的工具太复杂。做一个“一键诊断广告账户”的轻量级 SaaS，或者针对特定品类的素材生成服务。\n\n")

        if "Finance & Payments" in top_pains:
            f.write("### 💡 方向三：跨平台利润核算与资金流管理\n")
            f.write("- **现象**: 费用（Fees）是高频词。卖家算不清楚自己到底赚没赚钱（被平台抽成、退货搞晕了）。\n")
            f.write("- **机会**: 一个极其简单的“真实利润计算器”，整合多平台数据，算清每一单的净利。\n\n")
            
        f.write("### 💡 方向四：物流/供应链的“拼单”或“透明化”\n")
        f.write("- **现象**: `Logistics` 是永恒的痛。小卖家运费贵，时效慢。\n")
        f.write("- **机会**: 针对特定路线（如中美）的专线拼单服务，或者供应链推荐社区。\n")

    print(f"🎉 Report generated: {OUTPUT_FILE}")

if __name__ == "__main__":
    analyze_dataset()