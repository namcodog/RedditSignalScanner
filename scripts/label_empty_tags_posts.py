import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


KNOWN_ENTITIES = {
    "amazon",
    "amazon_fba",
    "etsy",
    "shopify",
    "shopify_plus",
    "tiktok",
    "tiktok_shop",
    "paypal",
    "stripe",
    "reddit",
    "youtube",
    "instagram",
    "facebook",
    "meta",
    "google",
    "apple",
    "ebay",
    "walmart",
    "aliexpress",
    "alibaba",
    "temu",
    "shein",
    "wechat",
    "whatsapp",
    "x",
}

KNOWN_ALIASES = {
    "amazon fba": "amazon_fba",
    "fba": "amazon_fba",
    "shopify plus": "shopify_plus",
    "tiktok shop": "tiktok_shop",
    "tik tok shop": "tiktok_shop",
    "tiktokshop": "tiktok_shop",
    "twitter": "x",
    "x.com": "x",
    "fb": "facebook",
    "meta ads": "meta",
    "google ads": "google",
}

DOMAIN_KEYWORDS = [
    "ecommerce",
    "e-commerce",
    "store",
    "shop",
    "seller",
    "merchant",
    "payment",
    "payout",
    "checkout",
    "subscription",
    "ads",
    "advertising",
    "marketing",
    "growth",
    "support",
    "refund",
    "chargeback",
    "policy",
    "ban",
    "suspended",
    "risk",
    "fraud",
    "compliance",
    "shipping",
    "logistics",
    "fulfillment",
    "warehouse",
    "inventory",
    "platform",
    "tool",
    "saas",
    "plugin",
    "api",
    "integration",
    "店铺",
    "卖家",
    "支付",
    "收款",
    "广告",
    "增长",
    "客服",
    "退款",
    "风控",
    "物流",
    "发货",
    "仓储",
    "平台",
    "工具",
    "合规",
]

ASK_KEYWORDS = [
    "how",
    "what",
    "why",
    "anyone",
    "can someone",
    "help",
    "advice",
    "suggest",
    "recommend",
    "question",
    "ask",
    "how to",
    "怎么",
    "如何",
    "求助",
    "请问",
    "问题",
    "有人知道",
]

COMPLAIN_KEYWORDS = [
    "sucks",
    "terrible",
    "awful",
    "hate",
    "worst",
    "scam",
    "fraud",
    "broken",
    "bug",
    "overpriced",
    "too expensive",
    "ban",
    "banned",
    "suspended",
    "locked",
    "freeze",
    "froze",
    "frozen",
    "no response",
    "chargeback",
    "投诉",
    "垃圾",
    "烂",
    "坑",
    "太贵",
    "封号",
    "冻结",
    "卡住",
    "被拒",
    "崩溃",
    "吐槽",
    "失望",
]

RECOMMEND_KEYWORDS = [
    "i recommend",
    "highly recommend",
    "recommend",
    "best tool",
    "best platform",
    "suggest",
    "use this",
    "should use",
    "值得",
    "推荐",
]

SOLUTION_KEYWORDS = [
    "solution",
    "fix",
    "resolved",
    "here is how",
    "steps",
    "guide",
    "tutorial",
    "we solved",
    "i solved",
    "方法",
    "解决",
    "教程",
    "指南",
]

NEWS_KEYWORDS = [
    "news",
    "announcement",
    "update",
    "press release",
    "官方公告",
    "更新",
    "公告",
]

POSITIVE_WORDS = [
    "great",
    "awesome",
    "love",
    "good",
    "excellent",
    "amazing",
    "works well",
    "满意",
    "好用",
    "不错",
    "推荐",
]

NEGATIVE_WORDS = [
    "bad",
    "terrible",
    "awful",
    "hate",
    "worst",
    "bug",
    "broken",
    "scam",
    "垃圾",
    "烂",
    "坑",
    "差",
    "糟糕",
    "失望",
]

PAIN_RULES = {
    "fee_high": ["fee", "fees", "cost", "expensive", "pricing", "price", "贵", "费用", "费率", "手续费"],
    "tax_confusion": ["tax", "vat", "duty", "关税", "税", "税务"],
    "account_ban": ["ban", "banned", "suspended", "account closed", "封号", "冻结"],
    "verification_blocked": ["verification", "verify", "kyc", "审核", "认证", "验证"],
    "support_unresponsive": ["support", "no response", "客服", "工单", "ticket"],
    "payout_delay": ["payout", "withdrawal", "settlement", "回款", "结算", "放款"],
    "payment_hold": ["hold", "on hold", "冻结资金", "资金冻结", "payment hold"],
    "refund_issue": ["refund", "退款"],
    "chargeback_risk": ["chargeback", "dispute", "拒付", "争议"],
    "fraud_risk": ["fraud", "scam", "欺诈", "骗子"],
    "compliance_risk": ["compliance", "合规"],
    "logistics_delay": ["shipping delay", "delayed shipping", "物流慢", "发货慢", "延迟发货"],
    "shipping_cost_high": ["shipping cost", "expensive shipping", "运费高", "物流费用高"],
    "integration_bug": ["api", "integration", "bug", "对接", "接口"],
    "policy_change": ["policy", "terms", "规则", "政策"],
    "ad_account_ban": ["ad account ban", "ads banned", "广告封号", "广告账号"],
    "ad_performance_drop": ["ad performance drop", "ads drop", "广告效果下降", "投放效果差"],
    "conversion_drop": ["conversion drop", "low conversion", "转化下降", "转化率低"],
    "tracking_issue": ["tracking issue", "pixel", "tracking", "追踪问题", "像素"],
    "data_inaccuracy": ["data inaccurate", "wrong data", "数据不准"],
    "onboarding_confusion": ["onboarding", "setup", "getting started", "新手", "入门"],
    "ui_confusing": ["ui confusing", "hard to use", "界面", "体验差", "难用"],
    "pricing_unclear": ["pricing unclear", "价格不清楚", "收费不明"],
    "low_roi": ["low roi", "roi低", "回报低"],
    "market_saturation": ["market saturation", "市场饱和"],
    "quality_inconsistent": ["quality inconsistent", "质量不稳定"],
    "counterfeit_risk": ["counterfeit", "fake", "假货"],
    "supply_instability": ["supply issue", "缺货", "供应不稳定"],
    "language_barrier": ["language barrier", "语言障碍"],
    "localization_issue": ["localization", "本地化"],
}

ASPECT_RULES = {
    "pricing": ["fee", "fees", "cost", "pricing", "price", "贵", "费用", "费率", "手续费"],
    "tax": ["tax", "vat", "duty", "关税", "税", "税务"],
    "payments": ["payment", "payout", "withdrawal", "settlement", "收款", "回款", "结算"],
    "refunds": ["refund", "退款"],
    "shipping": ["shipping", "fulfillment", "发货", "运费", "物流"],
    "logistics": ["logistics", "warehouse", "仓储", "物流"],
    "support": ["support", "客服", "工单", "ticket"],
    "policy": ["policy", "terms", "规则", "政策"],
    "ux": ["ux", "ui", "hard to use", "体验", "难用", "界面"],
    "onboarding": ["onboarding", "setup", "getting started", "入门", "新手"],
    "integration": ["api", "integration", "plugin", "对接", "接口"],
    "automation": ["automation", "自动化"],
    "analytics": ["analytics", "report", "数据", "统计"],
    "performance": ["performance", "slow", "速度", "卡"],
    "reliability": ["down", "outage", "稳定性"],
    "security": ["security", "安全", "hack"],
    "compliance": ["compliance", "合规"],
    "fraud": ["fraud", "scam", "欺诈"],
    "inventory": ["inventory", "stock", "库存"],
    "marketing": ["marketing", "growth", "增长", "获客"],
    "ads": ["ads", "advertising", "广告", "投放"],
    "conversion": ["conversion", "转化"],
    "attribution": ["attribution", "归因"],
    "reviews": ["review", "rating", "评论"],
    "community": ["community", "subreddit", "forum", "reddit", "社区"],
}

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "from",
    "about",
    "have",
    "has",
    "been",
    "your",
    "you",
    "our",
    "their",
    "they",
    "them",
    "just",
    "like",
    "love",
    "best",
    "need",
    "want",
    "help",
    "issue",
    "problem",
    "update",
    "news",
    "guide",
    "tips",
}


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    return any(kw in text for kw in keywords)


def _normalize_entity(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip().lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned


def extract_entities(text: str, text_original: str) -> Dict[str, List[str]]:
    known: List[str] = []
    new: List[str] = []
    seen = set()

    text_lower = text.lower()
    for alias, canonical in KNOWN_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", text_lower):
            if canonical not in seen:
                known.append(canonical)
                seen.add(canonical)

    for ent in KNOWN_ENTITIES:
        ent_phrase = ent.replace("_", " ")
        if re.search(rf"\b{re.escape(ent_phrase)}\b", text_lower):
            if ent not in seen:
                known.append(ent)
                seen.add(ent)

    for match in re.findall(r"https?://(?:www\.)?([a-zA-Z0-9.-]+)", text_lower):
        base = match.split("/")[0]
        parts = base.split(".")
        if len(parts) >= 2:
            candidate = parts[-2]
        else:
            candidate = base
        candidate = _normalize_entity(candidate)
        if candidate and candidate not in KNOWN_ENTITIES and candidate not in seen:
            new.append(candidate)
            seen.add(candidate)

    for token in re.findall(r"\b[A-Z][A-Za-z0-9]{2,}\b", text_original):
        norm = _normalize_entity(token)
        if norm and norm not in KNOWN_ENTITIES and norm not in seen and norm not in STOPWORDS:
            new.append(norm)
            seen.add(norm)

    return {"known": known, "new": new}


def detect_intent(text: str, domain_related: bool) -> str:
    if _contains_any(text, COMPLAIN_KEYWORDS):
        return "complain"
    if _contains_any(text, ASK_KEYWORDS) or "?" in text:
        return "ask_help"
    if _contains_any(text, RECOMMEND_KEYWORDS):
        return "recommend_product"
    if _contains_any(text, SOLUTION_KEYWORDS):
        return "share_solution"
    if domain_related:
        return "share_solution"
    return "offtopic"


def detect_content_type(main_intent: str, text: str) -> str:
    if main_intent == "ask_help":
        return "ask_question"
    if main_intent == "complain":
        return "rant"
    if main_intent == "recommend_product":
        return "user_review"
    if main_intent == "share_solution":
        return "discussion"
    if _contains_any(text, NEWS_KEYWORDS):
        return "news_sharing"
    return "other"


def detect_sentiment(main_intent: str, text: str) -> float:
    if main_intent == "complain":
        return -0.6 if _contains_any(text, NEGATIVE_WORDS) else -0.3
    if main_intent == "recommend_product":
        return 0.7 if _contains_any(text, POSITIVE_WORDS) else 0.5
    if main_intent == "share_solution":
        return 0.3 if _contains_any(text, POSITIVE_WORDS) else 0.1
    if main_intent == "ask_help":
        return -0.1 if _contains_any(text, NEGATIVE_WORDS) else 0.1
    return 0.0


def detect_purchase_intent(text: str, main_intent: str) -> float:
    strong_buy = ["buy now", "ready to buy", "pay now", "subscribe now", "sign up now", "立即购买", "马上买"]
    buy_terms = ["buy", "purchase", "price", "pricing", "cost", "quote", "trial", "subscribe", "plan", "付费", "订阅", "试用", "价格", "购买"]
    compare_terms = ["recommend", "suggest", "which", "best", "alternative", "比较", "哪个好"]

    if _contains_any(text, strong_buy):
        return 0.8
    if _contains_any(text, buy_terms):
        return 0.5
    if _contains_any(text, compare_terms):
        return 0.4
    if main_intent in {"ask_help", "complain"}:
        return 0.2
    if main_intent == "recommend_product":
        return 0.2
    if main_intent == "share_solution":
        return 0.1
    return 0.0


def detect_tags(text: str) -> Tuple[List[str], List[str]]:
    pain_tags: List[str] = []
    aspect_tags: List[str] = []

    for tag, keywords in PAIN_RULES.items():
        if _contains_any(text, keywords):
            pain_tags.append(tag)

    for tag, keywords in ASPECT_RULES.items():
        if _contains_any(text, keywords):
            aspect_tags.append(tag)

    if "pricing" in aspect_tags and "fee_high" not in pain_tags and _contains_any(text, NEGATIVE_WORDS):
        pain_tags.append("fee_high")

    if "tax" in aspect_tags and "tax_confusion" not in pain_tags:
        pain_tags.append("tax_confusion")

    if _contains_any(text, ["shipping", "物流", "发货"]) and "shipping" not in aspect_tags:
        aspect_tags.append("shipping")

    if _contains_any(text, ["logistics", "仓储"]) and "logistics" not in aspect_tags:
        aspect_tags.append("logistics")

    return pain_tags[:3], aspect_tags[:3]


def label_post(row: Dict[str, object]) -> Dict[str, object]:
    title = str(row.get("title") or "")
    body = str(row.get("body") or "")
    url = str(row.get("url") or "")
    text_original = f"{title} {body} {url}".strip()
    text_lower = text_original.lower()

    entities = extract_entities(text_lower, text_original)
    domain_related = bool(entities["known"] or entities["new"] or _contains_any(text_lower, DOMAIN_KEYWORDS))

    main_intent = detect_intent(text_lower, domain_related)
    content_type = detect_content_type(main_intent, text_lower)
    sentiment = detect_sentiment(main_intent, text_lower)
    purchase_intent_score = detect_purchase_intent(text_lower, main_intent)
    pain_tags, aspect_tags = detect_tags(text_lower)

    if main_intent != "offtopic" and not pain_tags and not aspect_tags:
        if domain_related:
            aspect_tags = ["community"]

    if main_intent == "offtopic":
        pain_tags = []
        aspect_tags = []
        entities = {"known": [], "new": []}

    crossborder_signals = {
        "mentions_shipping": _contains_any(
            text_lower,
            ["shipping", "logistics", "跨境", "清关", "海关", "国际运费", "运费", "物流", "发货"],
        ),
        "mentions_tax": _contains_any(text_lower, ["tax", "vat", "duty", "关税", "税", "税务"]),
    }

    return {
        "id": int(row["id"]),
        "content_type": content_type,
        "main_intent": main_intent,
        "sentiment": float(sentiment),
        "pain_tags": pain_tags[:3],
        "aspect_tags": aspect_tags[:3],
        "entities": entities,
        "crossborder_signals": crossborder_signals,
        "purchase_intent_score": float(purchase_intent_score),
    }


def validate_output_line(line: Dict[str, object]) -> None:
    required_keys = {
        "id",
        "content_type",
        "main_intent",
        "sentiment",
        "pain_tags",
        "aspect_tags",
        "entities",
        "crossborder_signals",
        "purchase_intent_score",
    }
    if set(line.keys()) != required_keys:
        raise ValueError("output keys mismatch")
    if not isinstance(line["id"], int):
        raise ValueError("id must be int")
    if line["content_type"] not in {"ask_question", "user_review", "news_sharing", "discussion", "rant", "other"}:
        raise ValueError("invalid content_type")
    if line["main_intent"] not in {"complain", "ask_help", "share_solution", "recommend_product", "offtopic"}:
        raise ValueError("invalid main_intent")
    if not (-1.0 <= line["sentiment"] <= 1.0):
        raise ValueError("sentiment out of range")
    if not (0.0 <= line["purchase_intent_score"] <= 1.0):
        raise ValueError("purchase_intent_score out of range")
    if len(line["pain_tags"]) > 3 or len(line["aspect_tags"]) > 3:
        raise ValueError("too many tags")


def run(input_path: Path, output_path: Path) -> int:
    count_in = 0
    count_out = 0
    with input_path.open("r", encoding="utf-8") as infile, output_path.open("w", encoding="utf-8") as outfile:
        for line in infile:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            labeled = label_post(row)
            validate_output_line(labeled)
            outfile.write(json.dumps(labeled, ensure_ascii=False) + "\n")
            count_in += 1
            count_out += 1

    if count_in != count_out:
        raise RuntimeError("line count mismatch")
    return count_out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    if not input_path.exists():
        print(f"input not found: {input_path}", file=sys.stderr)
        return 1

    total = run(input_path, output_path)
    print(f"wrote {total} lines to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
