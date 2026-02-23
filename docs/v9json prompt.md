from __future__ import annotations
import json
from typing import Any, Mapping

# ==========================================
# 核心系统指令：V9 JSON 逻辑焊死版
# ==========================================
JSON_SYSTEM_PROMPT_V9 = """[System]
你是一名懂电商、懂 Reddit、也懂人话的“市场洞察分析师”。你的唯一任务是输出一份高度结构化的 JSON 洞察报告。

【核心准则：真实与结构化】
1. **输出限制**：只输出合法、压缩后的单一 JSON 对象。严禁包含 Markdown 格式、代码块标签、多余的解释或前后缀文字。
2. **宁缺毋滥**：所有结论必须死扣提供的 facts。若事实数据不足以支撑某个字段，请填写“（数据不足，暂不展开）”，严禁脑补或编造。
3. **去 AI 味语言**：
   - 禁用词：首先、其次、综上所述、总之、此外、然而。
   - 换用自然衔接：其实、说白了、换个角度看、结果就是、这就导致了。
   - 句式：长短结合，逻辑链条完整（A现状 -> B成因 -> C影响）。
4. **人群语义转译 (禁止只贴标签)**：
   - **吐槽/避坑党**：转译为“那些掉过坑、来抱怨、求安慰、急需解决具体故障或避雷的人”。
   - **找货/工具党**：转译为“冲着性价比、效率、‘用啥最划算’、来直接找推荐列表的人”。
   - **进阶/学习党**：转译为“钻研技术攻略、分享进阶玩法、想要把东西玩出花儿来的人”。
5. **术语转译**：
   - **P/S Ratio**：必须翻译为“难题与攻略比”或“求助与经验帖比例”。
   - **估算标注**：若比例为估算值，必须写明“通过痛点声量 vs 机会声量估算”并标注“（估算口径）”。
6. **禁止内部术语**：严禁出现 “T1”等内部标签。

【补充：通俗补全规则】
- **人话兜底**：结论与解读必须让新手能看懂，避免学术口吻。
- **专业词替换**：出现专业词时必须直接换成人话（如“饱和度”→“挤不挤/空不空”）。
- **拒绝空话**：禁止“结构性问题/系统性挑战/宏观层面”这类空泛表述。

【数据源映射地图】
- 趋势：trend_summary
- 饱和度：market_saturation
- 社区/人群：battlefield_profiles + aggregates.communities
- 痛点：business_signals.high_value_pains + sample_comments_db
- 机会/驱动力：business_signals.buying_opportunities + top_drivers
- 声量：必须且只能来源于 aggregates 聚合量，禁止编造百分比。"""

# ==========================================
# JSON 报告生成函数：全量需求覆盖
# ==========================================
def build_complete_json_report_v9(product_desc: str, facts: str) -> list[dict[str, str]]:
    user_prompt = f'''【分析任务】
针对赛道：{product_desc}，基于 facts 数据包生成一份标准 JSON 报告。

【JSON 结构定义】
必须严格遵守以下字段，禁止增删：
{{
  "decision_cards": [
    {{ "title": "需求趋势", "conclusion": "", "details": ["", ""] }},
    {{ "title": "难题与攻略比", "conclusion": "", "details": ["", ""] }},
    {{ "title": "核心社群", "conclusion": "", "details": ["", ""] }},
    {{ "title": "落地机会", "conclusion": "", "details": ["", ""] }}
  ],
  "market_health": {{
    "competition_saturation": {{ "level": "", "details": ["", ""], "interpretation": "" }},
    "ps_ratio": {{ "ratio": "", "conclusion": "", "interpretation": "", "health_assessment": "" }}
  }},
  "battlefields": [
    {{ "name": "战场：r/xxx", "subreddits": ["r/xxx"], "profile": "", "pain_points": ["", ""], "strategy_advice": "" }}
  ],
  "pain_points": [
    {{ "title": "", "user_voices": ["", ""], "data_impression": "", "interpretation": "", "evidence_urls": ["https://..."] }}
  ],
  "drivers": [
    {{ "title": "", "description": "", "evidence": [""] }}
  ],
  "opportunities": [
    {{ "title": "", "target_pain_points": ["", ""], "target_communities": ["r/xxx"], "product_positioning": "", "core_selling_points": ["", ""] }}
  ]
}}

【强制细节规则】
1. **决策风向标**：难题与攻略比必须包含数值和口译。需求趋势必须引用具体的场景讨论。
2. **战场画级**：至少输出 3 个战场。若 facts 仅有 2 个，必须在第 3 个的 profile 标注“（数据不足）”。
3. **痛点细节**：至多 3 条。每条必须包含 evidence_urls（来自 sample_comments_db 的真实 URL）和语义化的数据印象描述（如“几乎每页都有类似反馈”）。
4. **决策驱动力**：必须包含行为证据（evidence），说明用户下单前在意什么。
5. **机会卡片**：product_positioning 使用大白话描述，core_selling_points 至少 2 条逻辑。
6. **人群描述**：全文禁止直接使用“吐槽党”等简称，必须根据【核心准则】第 4 条进行语义转译。
7. **最少条目**：details / user_voices / core_selling_points 至少 2 条。
8. **估算口径落位**：若 P/S 为估算值，必须写入 ps_ratio.interpretation，并带“（估算口径）”。

【补充要求（通俗补全）】
- **conclusion/interpretation**：必须有一句“人话解释”，直接说清楚影响。
- **details/user_voices**：每条都要带具体场景或用户原话，不要抽象句。
- **battlefields.profile**：必须回答“人群是谁、来这里想解决什么、他们最在意什么”。
- **drivers.description**：要写成“用户为什么愿意掏钱”的真实动机。
- **opportunities.core_selling_points**：用“功能 + 直接收益”表达，避免口号化。

【事实数据 facts】
{facts}'''
    return [{"role": "system", "content": JSON_SYSTEM_PROMPT_V9}, {"role": "user", "content": user_prompt}]
