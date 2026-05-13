from __future__ import annotations

from app.services.hotpost.card_content_rules_config import load_card_content_rules
from app.services.hotpost.reddit_guide_prompt_assets import (
    build_reddit_guide_prompt_prefix,
    load_breakdown_compact_prompt,
    load_breakdown_field_semantics,
    load_hot_compact_prompt,
    load_hot_field_semantics,
    load_shared_base_prompt,
    load_reddit_guide_few_shots,
    load_reddit_guide_soul_prompt,
    load_signal_compact_prompt,
    load_signal_field_semantics,
    load_reddit_guide_thinking_contract,
)


def _flatten_banned_patterns(rules: dict) -> set[str]:
    patterns = rules.get("banned_patterns") or {}
    flattened: set[str] = set()
    for item in patterns.get("global", []):
        flattened.add(str(item))
    for items in (patterns.get("field_specific") or {}).values():
        for item in items:
            flattened.add(str(item))
    return flattened


def test_reddit_guide_prompt_assets_load_real_role_contract() -> None:
    soul = load_reddit_guide_soul_prompt()
    thinking = load_reddit_guide_thinking_contract()
    few_shots = load_reddit_guide_few_shots()
    shared_base = load_shared_base_prompt()
    field_semantics = load_signal_field_semantics()
    signal_compact = load_signal_compact_prompt()
    hot_compact = load_hot_compact_prompt()
    hot_field_semantics = load_hot_field_semantics()
    breakdown_compact = load_breakdown_compact_prompt()
    breakdown_field_semantics = load_breakdown_field_semantics()

    assert "你是“R站资深专家”" in shared_base
    assert "只用输入证据，不补背景" in shared_base
    assert "先保逻辑，再收句子" in shared_base
    assert "输出必须是合法 JSON" in shared_base
    assert "R站老炮儿" in soul
    assert "未美化需求数据库" in soul
    assert "每条吐槽都是一张没填金额的支票" in soul
    assert "Reddit 评论区里那些普通人翻不到的真金白银" in soul
    assert "正确的废话" in soul
    assert "你先判断，再表达" in thinking
    assert "需求雷达" in thinking
    assert "I hate it when" in thinking
    assert "Just switched from X to Y" in thinking
    assert "潜力快帖字段边界" in field_semantics
    assert "证据强弱这样处理" in field_semantics
    assert "一条原话，只能写成“有人开始这么看”" in field_semantics
    assert "正确但没新增判断的废话" in thinking
    assert "潜力快帖示例" in few_shots
    assert "Meta 投手不是在骂今天波动，是一个月都跑不顺" in few_shots
    assert "判断重点从单日系统波动，转到整月投放表现是否失稳" in few_shots
    assert "这条会影响投手怎么放预算" not in few_shots
    assert "past month 和 the whole month" in few_shots
    assert "近期爆帖示例" in few_shots
    assert "GEO 讨论升温，增长团队怀疑 SEO 老打法" in few_shots
    assert "评论区从围观 GEO 这个新词，转到站队旧 SEO 到底还灵不灵" in few_shots
    assert "这条会影响增长团队下一步怎么分工" not in few_shots
    assert "still works at all 把分歧说清了" in few_shots
    assert "当前写的是「潜力快帖」" in signal_compact
    assert "这张卡只回答一件事：谁开始把原来的判断顺序换掉了" in signal_compact
    assert "它讲的是“规则刚变”或“先后手刚换”" in signal_compact
    assert "不要写“原话里说……翻过来就是……”" in signal_compact
    assert "这帖为什么突然火了" in hot_compact
    assert "火的是这条帖，不一定是整个行业" in hot_compact
    assert "不要借一条热帖偷渡大结论" in hot_compact
    assert "冲突线比情绪强度更重要" in hot_compact
    assert "必须能压成一句对打句" in hot_compact
    assert "why_test_now 必须中文为主" in hot_compact
    assert "一张热点卡只回答两件事" in hot_field_semantics
    assert "一条爆帖，足够你写“这帖火在哪、大家在吵什么”" in hot_field_semantics
    assert "别借一条热帖偷渡大结论" in hot_field_semantics
    assert "判断逻辑第一" in hot_field_semantics
    assert "冲突线比情绪强度更重要" in hot_field_semantics
    assert "不要求双方声量对称" in hot_field_semantics
    assert "方法之争、优先级之争也可以算争议线" in hot_field_semantics
    assert "如果两者冲突，先保逻辑" in hot_field_semantics
    assert "必须中文为主" in hot_field_semantics
    assert "不写解释句，不超过一行" in hot_field_semantics
    assert "不要自己加带道德审判味的狠词" in hot_field_semantics
    assert "不能只留下情绪标签" in hot_field_semantics
    assert "不要把 fight_line 写成情绪播报" in hot_field_semantics
    assert "flashpoint：写清这帖为什么火" in hot_field_semantics
    assert "fight_line：写清评论区到底在吵哪条线" in hot_field_semantics
    assert "pain_point：" not in hot_field_semantics
    assert "target_user_and_scene：" not in hot_field_semantics
    assert "跨区热议 / 拆解卡" in breakdown_compact
    assert "不是更长一点的 signal" in breakdown_compact
    assert "thesis 是硬门槛" in breakdown_compact
    assert "至少 2 条原话要共同支撑同一条 thesis" in breakdown_compact
    assert "不要重复 current_card 已经说过的话" in breakdown_compact
    assert "如果只是同主题共现，不算成立" in breakdown_compact
    assert "跨区热议字段边界" in breakdown_field_semantics
    assert "多条讨论共同撑住了什么更深判断" in breakdown_field_semantics
    assert "title_hooks：最多 2 条" in breakdown_field_semantics
    assert "不要把 breakdown 写成长一点的 signal" in breakdown_field_semantics
    assert "至少 2 条原话要共同支撑同一条 thesis" in breakdown_field_semantics
    assert "不要把几条帖子写成“同主题拼盘”" in breakdown_field_semantics
    assert "thesis：这张卡最核心的新判断" in breakdown_field_semantics
    assert "flashpoint：" not in breakdown_field_semantics
    assert "fight_line：" not in breakdown_field_semantics


def test_reddit_guide_prompt_prefix_stamps_mode_name() -> None:
    prefix = build_reddit_guide_prompt_prefix(mode_name="潜力快帖")

    assert "当前输出模式：潜力快帖。" in prefix
    assert "你是“R站资深专家”" in prefix
    assert "只用输入证据，不补背景" in prefix
    assert "潜力快帖字段边界" in prefix
    assert "why_now 只回答“现在变了什么”" in prefix
    assert "why_test_now：只解释哪条证据撑住判断" in prefix
    assert "如果更多社区出现同样抱怨，就继续关注" not in prefix
    assert "好输出参考" in prefix
    assert "每个字段只回答一个问题，不互相抢活" in prefix
    assert "证据强弱这样处理" in prefix
    assert "近期爆帖示例" not in prefix
    assert "Reddit 是全球最大的未美化需求数据库" not in prefix
    assert len(prefix) <= 3200


def test_reddit_guide_hot_prompt_prefix_uses_hot_contract() -> None:
    prefix = build_reddit_guide_prompt_prefix(mode_name="近期爆帖")

    assert "当前输出模式：近期爆帖。" in prefix
    assert "这帖为什么突然火了" in prefix
    assert "一张热点卡只回答两件事" in prefix
    assert "近期爆帖示例" in prefix
    assert "GEO 讨论升温，增长团队怀疑 SEO 老打法" in prefix
    assert "火的是这条帖，不一定是整个行业" in prefix
    assert "冲突线比情绪强度更重要" in prefix
    assert "必须能压成一句对打句" in prefix
    assert "评论区从围观 GEO 这个新词，转到站队旧 SEO 到底还灵不灵" in prefix
    assert "flashpoint：写清这帖为什么火" in prefix
    assert "fight_line：写清评论区到底在吵哪条线" in prefix
    assert "pain_point：" not in prefix
    assert "target_user_and_scene：" not in prefix
    assert "潜力快帖字段边界" not in prefix
    assert "为什么现在发生变化" not in prefix
    assert "需求雷达" not in prefix
    assert len(prefix) <= 3200


def test_reddit_guide_breakdown_prompt_prefix_uses_breakdown_contract() -> None:
    prefix = build_reddit_guide_prompt_prefix(mode_name="跨区热议")

    assert "当前输出模式：跨区热议。" in prefix
    assert "跨区热议 / 拆解卡" in prefix
    assert "不是更长一点的 signal" in prefix
    assert "跨区热议字段边界" in prefix
    assert "多条讨论共同撑住了什么更深判断" in prefix
    assert "跨区热议示例" in prefix
    assert "CRM 回填最烦的，不是多点几下，是像在替经理补记录" in prefix
    assert "title_hooks：最多 2 条" in prefix
    assert "不要把 breakdown 写成长一点的 signal" in prefix
    assert "需求雷达" not in prefix
    assert "Reddit 是全球最大的未美化需求数据库" not in prefix
    assert len(prefix) <= 3200


def test_prompt_assets_absorb_v12_high_density_concise_rules() -> None:
    shared_base = load_shared_base_prompt()
    signal_contract = load_signal_compact_prompt() + load_signal_field_semantics()
    hot_contract = load_hot_compact_prompt() + load_hot_field_semantics()
    breakdown_contract = load_breakdown_compact_prompt() + load_breakdown_field_semantics()
    all_contracts = "\n".join([shared_base, signal_contract, hot_contract, breakdown_contract])

    assert "简洁不是压缩信息" in shared_base
    assert "核心判断、必要证据和具体对象" in shared_base
    assert "删重复解释、铺垫句、报告式连接词" in shared_base
    assert "summary_line 先给核心判断" in all_contracts
    assert "why_now 只回答“现在变了什么”" in signal_contract
    assert "不要顺手给行动建议" in signal_contract
    assert "why_test_now 只解释哪条证据撑住判断" in all_contracts
    assert "不重复 why_now" in all_contracts
    assert "不贴残缺英文" in all_contracts
    assert "标题党情绪词" in all_contracts
    assert "工具开始强调" in all_contracts
    assert "厂商开始宣传" in all_contracts
    assert "AI 代理" in all_contracts
    assert "AI SEO" in all_contracts
    assert "Claude" in all_contracts


def test_prompt_assets_absorb_v13_title_standalone_rules() -> None:
    shared_base = load_shared_base_prompt()
    signal_contract = load_signal_compact_prompt() + load_signal_field_semantics()
    hot_contract = load_hot_compact_prompt() + load_hot_field_semantics()
    breakdown_contract = load_breakdown_compact_prompt() + load_breakdown_field_semantics()
    few_shots = load_reddit_guide_few_shots()
    all_contracts = "\n".join([shared_base, signal_contract, hot_contract, breakdown_contract, few_shots])

    assert "首页可扫读标题" in shared_base
    assert "18-32" in all_contracts
    assert "默认不写 r/xxxx 社区名" in all_contracts
    assert "出现了什么明确变化" in all_contracts
    assert "Shopify 卖家" in all_contracts
    assert "不看 summary_line" in all_contracts
    assert "不要为了短牺牲关键对象" in all_contracts
    assert "800行提示词" in all_contracts
    assert "全自动 AI 代理" in all_contracts
    assert "API 账单" in all_contracts
    assert "AI自动化" not in all_contracts
    assert "API账单" not in all_contracts
    assert "遭评论区质疑" not in all_contracts


def test_card_content_rules_absorb_v12_banned_and_rewrite_terms() -> None:
    load_card_content_rules.cache_clear()
    try:
        rules = load_card_content_rules()
    finally:
        load_card_content_rules.cache_clear()
    banned = _flatten_banned_patterns(rules)
    rewrite_phrases = (rules.get("semantic_readout") or {}).get("rewrite_phrases") or {}

    for phrase in [
        "这说明",
        "这改变了",
        "这句话把",
        "下一步",
        "应该先",
        "直接说明了",
        "直接点出了",
        "已经从",
        "转移到了",
        "真正",
        "梦碎",
        "翻车",
        "炸了",
        "神了",
        "封神",
        "工具开始强调",
        "产品开始强调",
        "方案开始强调",
    ]:
        assert phrase in banned

    assert rewrite_phrases["这说明判断依据已经从 A 转移到了 B"] == "判断重点从 A 转向 B"
    assert rewrite_phrases["工具开始强调"] == "厂商开始宣传"
    assert rewrite_phrases["产品开始强调"] == "产品页面开始主打"
    assert rewrite_phrases["方案开始强调"] == "团队开始主打"


def test_card_content_rules_absorb_v13_title_standalone_terms() -> None:
    load_card_content_rules.cache_clear()
    try:
        rules = load_card_content_rules()
    finally:
        load_card_content_rules.cache_clear()
    banned = _flatten_banned_patterns(rules)
    title_guidance = (rules.get("title_standalone") or {}).get("rewrite_guidance") or {}

    for phrase in [
        "这到底是什么",
        "所以呢",
        "这是什么",
        "它到底",
        "这事",
        "实际效用",
        "定义与",
        "遭评论区",
        "评估AI",
        "API账单",
        "AI自动化",
        "全自动AI代理",
        "这帖火了",
        "这帖火在",
        "评论区在吵",
        "有用户开始",
        "开始先",
        "不再先",
    ]:
        assert phrase in banned

    assert title_guidance["写了800行提示词，评论区却在问：这到底是什么？"] == "800行提示词被评论区追问定义和实际用途"
    assert title_guidance["想用 AI 自动干活，先算清调教时间和模型账单"] == "用 AI 自动干活前，先算调提示词时间和 API 账单"
    assert title_guidance["r/flashlight 用户拒绝内置电池手电，转向多支可换 21700 电池组合"] == "手电玩家放弃内置电池，转向可换 21700 电池组合"
    assert title_guidance["全自动 AI 代理行不通，开发者转向“智能助手”"] == "全自动 AI 代理难落地，开发者转向受控智能助手"
    assert (
        title_guidance["移动端转化率卡在2.1%，先看20-30个用户会话回放定位问题"]
        == "Shopify 卖家移动端 checkout 转化率卡在2.1%，先看用户会话回放"
    )
