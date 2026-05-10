from __future__ import annotations

import json
import re
from typing import Any


TITLE_ONLY_FIELDS = {"title"}

VAGUE_TITLE_PATTERNS = (
    "这到底是什么",
    "所以呢",
    "这是什么",
    "它到底",
    "这事",
)
CLICKBAIT_TITLE_WORDS = ("梦碎", "翻车", "炸了", "神了", "封神")
COMPACT_ENGLISH_ABBR_RE = re.compile(
    r"[\u4e00-\u9fff](?:AI|API|SEO|GEO|ROI|LLM|Claude|OpenAI|ChatGPT|Gemini|DeepSeek|Token|Tokens)"
    r"|(?:AI|API|SEO|GEO|ROI|LLM|Claude|OpenAI|ChatGPT|Gemini|DeepSeek|Token|Tokens)[\u4e00-\u9fff]"
)
REPORT_TITLE_WORDS = (
    "实际效用",
    "定义与",
    "遭评论区",
    "评估AI",
)
COMMUNITY_TITLE_RE = re.compile(r"(?:^|[\s，,。；;：:])r/[A-Za-z0-9_][A-Za-z0-9_]{1,30}")
TITLE_TEMPLATE_PATTERNS = (
    "这帖火了",
    "这帖火在",
    "这帖火的点",
    "这帖突然火了",
    "评论区在吵",
    "评论区先吵",
    "大家在吵",
    "有用户开始",
    "用户开始",
    "开始先",
    "不再先",
    "先看",
    "先问",
    "先算",
    "不是",
    "而是",
)
BUSINESS_CONTEXT_HINTS = (
    "移动端",
    "转化率",
    "checkout",
    "会话回放",
    "广告",
    "投放",
    "API 账单",
    "API账单",
    "模型账单",
    "客服",
    "CRM",
)
CONCRETE_SUBJECT_MARKERS = (
    "Shopify",
    "Amazon",
    "亚马逊",
    "Meta",
    "Google",
    "Claude",
    "OpenAI",
    "ChatGPT",
    "卖家",
    "商家",
    "店主",
    "电商",
    "开发者",
    "投手",
    "产品经理",
    "客服团队",
    "服务商",
    "厂商",
    "程序员",
    "评论区",
)


def find_v13_title_issues(generated: dict[str, Any]) -> list[str]:
    title = str(generated.get("title") or "")
    summary = str(generated.get("summary_line") or "")
    context_text = "\n".join(
        str(generated.get(key) or "")
        for key in ("summary_line", "audience", "why_now", "why_test_now", "flashpoint", "fight_line", "thesis")
    )
    issues: list[str] = []
    if not title:
        issues.append("title: 缺少标题。")
        return issues
    for pattern in VAGUE_TITLE_PATTERNS:
        if pattern in title:
            issues.append(f"title: 出现依赖 summary_line 才能看懂的指代 `{pattern}`。")
    clickbait_hits = [word for word in CLICKBAIT_TITLE_WORDS if word in title]
    if clickbait_hits:
        issues.append(f"title: 出现标题党式压缩词 {clickbait_hits[:3]}，要改成具体发生了什么。")
    if COMPACT_ENGLISH_ABBR_RE.search(title):
        issues.append("title: 英文缩写、产品名或英文词和中文挤在一起，需要写成 `AI 自动化`、`API 账单`、`Claude Code 自动投递` 这类可读排版。")
    report_hits = [word for word in REPORT_TITLE_WORDS if word in title]
    if report_hits:
        issues.append(f"title: 出现书面词或报告腔 {report_hits[:3]}，要改成大众能一眼懂的话。")
    if COMMUNITY_TITLE_RE.search(title):
        issues.append("title: 默认不要把 r/xxxx 社区名写进标题；除非社区名本身就是事件主体，否则改成真实人群或对象。")
    template_hits = [word for word in TITLE_TEMPLATE_PATTERNS if word in title]
    if template_hits:
        issues.append(
            f"title: 出现高频模板句式 {template_hits[:4]}，要改成干净中文短句，不要套“开始/先/再/不是...是...”结构。"
        )
    if len(title) > 36:
        issues.append("title: 首页标题过长，优先压到 18-32 个中文字；中英混排最多放宽到 36 字，并用中文逗号拆清停顿。")
    if any(hint in title for hint in BUSINESS_CONTEXT_HINTS):
        context_subject_hits = [marker for marker in CONCRETE_SUBJECT_MARKERS if marker in context_text]
        title_subject_hits = [marker for marker in CONCRETE_SUBJECT_MARKERS if marker in title]
        if context_subject_hits and not title_subject_hits:
            issues.append(
                "title: 缺少主体或业务场景；不能只写移动端、转化率、账单这类对象，要把 Shopify 卖家、开发者、投手等真实主体写进标题。"
            )
    if len(title) < 12 and summary:
        issues.append("title: 标题过短，像钩子，不像能独立理解的微摘要。")
    return issues


def build_title_independence_repair_messages(
    *,
    generated: dict[str, Any],
    semantic_brief: dict[str, Any],
    issues: list[str],
    semantic_model: str,
    writer_model: str,
) -> list[dict[str, str]]:
    issue_text = "\n".join(f"- {issue}" for issue in issues[:12]) or "- 本轮仍需主动检查 title 是否能独立看懂。"
    context = {
        "semantic_model": semantic_model,
        "writer_model": writer_model,
        "semantic_brief": semantic_brief,
        "current_fields_for_context": {
            key: value
            for key, value in generated.items()
            if key in {"title", "summary_line", "why_now", "why_test_now", "flashpoint", "fight_line", "thesis"}
        },
        "task": "只改 title，让它不看 summary_line 也能独立看懂；只允许输出 title 字段的 JSON。",
        "bad_examples": [
            "写了800行提示词，评论区却在问：这到底是什么？",
            "全自动 AI 代理梦碎：开发者承认，能上线的只有智能助手",
            "开源模型跑分高没用，先问服务商有没有偷偷量化",
            "用 Claude Code 自动投简历拿 12 个面试，但 Token 消耗惊人，值不值？",
            "顾问警告：多数企业级 Shopify 店铺用 Headless 是错的，应先问 Shopify Plus 隐藏条款",
            "移动端转化率卡在2.1%，先看20-30个用户会话回放定位问题",
            "欧洲 SPF 唇部买家开始把有色润唇和唇油当作防晒新选择，同时哑光 SPF 润唇膏出现空白",
            "r/flashlight 用户拒绝内置电池手电，转向多支可换 21700 电池组合",
        ],
        "better_examples": [
            "800行提示词没讲清价值，评论区质疑它到底有什么用",
            "全自动 AI 代理上线太难，开发者改做受控智能助手",
            "用 AI 自动干活前，先算调提示词时间和 API 账单",
            "模型跑分高也可能变笨，因为服务商可能偷偷量化",
            "Claude Code 自动投 740 份简历拿 12 个面试，但 Token 成本太高",
            "多数 Shopify 大店不该先上 Headless，要先问 Plus 隐藏条款",
            "Shopify 卖家移动端 checkout 转化率卡住，先看用户会话回放",
            "欧洲 SPF 唇部买家，把有色润唇和唇油当成防晒新选择",
            "手电玩家放弃内置电池，转向可换 21700 电池组合",
        ],
    }
    system = """
你是中文卡片标题编辑。你的任务不是写吸睛标题，而是把 title 改成能独立理解的微摘要。

硬要求：
- 只输出 JSON，不输出解释。
- 只允许输出 title，一个字段；不要输出 summary_line、why_now 或其他字段。
- 不新增事实，不扩大判断，不改卡片立场。
- title 必须不看 summary_line 也能懂，但它首先是首页可扫读标题，不是报告标题。
- title 只回答：谁，在什么对象上，出现了什么明确变化；不要把证据、社区名、解释、二级转折都塞进标题。
- 原有对象、变化/冲突和核心意思不能丢；后果能放进 summary_line 时，不要硬塞进 title。
- 主体不能藏在 summary_line 里；如果上下文是 Shopify 卖家、开发者、投手、产品经理、客服团队，title 里要写出来。
- 社区名默认不进标题；除非 r/xxxx 本身就是事件主体，否则改成真实人群或对象。
- 不要只写钩子，不要写“这到底是什么”“所以呢”“它到底”这种需要上下文才能懂的指代。
- 不要统一套模板；少用“开始、先、再、不是……是……、这帖火了、评论区在吵、有用户”。
- 需要停顿时用中文逗号拆开，例如“欧洲 SPF 唇部买家，把有色润唇和唇油当成防晒新选择”。
- 不要为了短而写标题党；禁用“梦碎、翻车、炸了、神了、封神”。
- 不要用“遭评论区质疑”“定义与实际效用”这种书面词；改成“评论区质疑它到底有什么用”。
- 不要写“评估AI自动化”“API账单”“用Claude Code自动投”“大量Token只换来”；英文缩写、产品名和英文词要留空格，写成“AI 自动化”“API 账单”“用 Claude Code 自动投”“大量 Token 只换来”。
- 保留具体对象，例如“800行提示词”“全自动 AI 代理”“模型跑分”“服务商量化”。
- 英文缩写和产品名保持可读排版，例如“AI 代理”“AI SEO”“Claude Code”“Token”。
- 优先 18-32 个中文字；中英混排可放宽，但超过 36 字必须二次压缩。
- 如果清楚和短冲突，先保留主体和具体对象，再删社区名、解释尾巴、二级转折和模板连接词。
- 当前组合模型口径：google/gemini-3-flash-preview 做语义理解，deepseek/deepseek-v4-pro 做中文标题编辑。
""".strip()
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": issue_text + "\n\n" + json.dumps(context, ensure_ascii=False, separators=(",", ":"))},
    ]


def merge_title_repair(original: dict[str, Any], repaired: dict[str, Any]) -> dict[str, Any]:
    merged = dict(original)
    if isinstance(repaired, dict) and isinstance(repaired.get("title"), str):
        merged["title"] = repaired["title"]
    return merged
