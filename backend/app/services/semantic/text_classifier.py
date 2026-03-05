from __future__ import annotations

import os
import re
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from app.interfaces.semantic_provider import SemanticLoadStrategy, SemanticProvider
from app.models.comment import Aspect, Category
from app.services.semantic.robust_loader import RobustSemanticLoader
from app.services.semantic.unified_lexicon import UnifiedLexicon
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_vader = SentimentIntensityAnalyzer()


def _load_classifier_keywords() -> dict[str, list[str]]:
    """Load classifier keyword lists from config file."""
    cfg_path = Path("backend/config/text_classifier_keywords.yml")
    if not cfg_path.exists():
        return {}
    try:
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        if isinstance(data, dict):
            return {k: list(v or []) for k, v in data.items()}
    except Exception:
        return {}
    return {}


_CLASSIFIER_KEYWORDS = _load_classifier_keywords()

PRICE_KWS = tuple(_CLASSIFIER_KEYWORDS.get("price_kws", []))
SUBS_KWS = tuple(_CLASSIFIER_KEYWORDS.get("subs_kws", []))
CONTENT_KWS = tuple(_CLASSIFIER_KEYWORDS.get("content_kws", []))
INSTALL_KWS = tuple(_CLASSIFIER_KEYWORDS.get("install_kws", []))
ECO_KWS = tuple(_CLASSIFIER_KEYWORDS.get("eco_kws", []))
STRENGTH_KWS = tuple(_CLASSIFIER_KEYWORDS.get("strength_kws", []))
SOLUTION_KWS = tuple(_CLASSIFIER_KEYWORDS.get("solution_kws", []))
STRONG_PAIN_KWS = tuple(_CLASSIFIER_KEYWORDS.get("strong_pain_kws", []))
WEAK_PAIN_KWS = tuple(_CLASSIFIER_KEYWORDS.get("weak_pain_kws", []))
_ASPECT_KEYWORDS: dict[str, list[str]] = {}
_ASPECT_KEYWORD_PATS: dict[str, list[re.Pattern[str]]] = {}


from sqlalchemy import create_engine, text
from app.core.config import get_settings

def _load_aspect_keywords() -> None:
    """从配置文件和数据库加载 Aspect 关键词。"""
    global _ASPECT_KEYWORDS, _ASPECT_KEYWORD_PATS
    if _ASPECT_KEYWORDS and _ASPECT_KEYWORD_PATS:
        return
    try:
        # 1. Load from YAML
        cfg_path = Path("backend/config/aspect_keywords.yml")
        if cfg_path.exists():
            data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            _ASPECT_KEYWORDS = data.get("aspect_mapping", {}) or {}
        
        # 2. Load from DB (Domain Pain Rules)
        try:
            settings = get_settings()
            # Use sync engine for loading rules
            db_url = settings.database_url.replace("asyncpg", "psycopg")
            engine = create_engine(db_url)
            with engine.connect() as conn:
                rows = conn.execute(text("""
                    SELECT term, aspect 
                    FROM semantic_rules 
                    WHERE rule_type IN ('domain_pain', 'vertical_pain', 'vertical_spec', 'vertical_slang')
                      AND is_active = true
                """)).fetchall()
                
            db_count = 0
            for term, aspect in rows:
                if aspect and term:
                    if aspect not in _ASPECT_KEYWORDS:
                        _ASPECT_KEYWORDS[aspect] = []
                    _ASPECT_KEYWORDS[aspect].append(str(term))
                    db_count += 1
            print(f"✅ Loaded {db_count} domain pain rules from DB")
            
        except Exception as e:
            print(f"⚠️ Failed to load rules from DB: {e}")

        # 3. Compile Regex
        pats: dict[str, list[re.Pattern[str]]] = {}
        for aspect_name, kws in _ASPECT_KEYWORDS.items():
            compiled: list[re.Pattern[str]] = []
            for kw in kws:
                kw = (kw or "").strip()
                if not kw:
                    continue
                # 用单词边界避免 cheap/steep 等误判；空格转 \\s+ 容错
                esc = re.escape(kw)
                if re.search(r"[A-Za-z0-9]", kw):
                    esc = esc.replace(r"\ ", r"\s+")
                    pat = re.compile(rf"\b{esc}\b", re.IGNORECASE)
                else:
                    pat = re.compile(esc, re.IGNORECASE)
                compiled.append(pat)
            if compiled:
                pats[aspect_name.lower()] = compiled
        _ASPECT_KEYWORD_PATS = pats
        print(f"✅ Loaded total {sum(len(v) for v in _ASPECT_KEYWORDS.values())} aspect keywords")
        
    except Exception as e:  # pragma: no cover - safe fallback
        print(f"⚠️ Failed to load aspect_keywords: {e}")
        _ASPECT_KEYWORDS, _ASPECT_KEYWORD_PATS = {}, {}


QUALITY_KWS = tuple(_CLASSIFIER_KEYWORDS.get("quality_kws", []))
SHIPPING_KWS = tuple(_CLASSIFIER_KEYWORDS.get("shipping_kws", []))
SERVICE_KWS = tuple(_CLASSIFIER_KEYWORDS.get("service_kws", []))
FUNCTION_KWS = tuple(_CLASSIFIER_KEYWORDS.get("function_kws", []))
UX_KWS = tuple(_CLASSIFIER_KEYWORDS.get("ux_kws", []))
RETURN_KWS = tuple(_CLASSIFIER_KEYWORDS.get("return_kws", []))

_LEX_FEATURE_PATS: List[Tuple[str, re.Pattern[str]]] | None = None
_LEX_PAIN_PATS: List[Tuple[str, re.Pattern[str]]] | None = None
_EXPANDED_PAIN_PATS: List[Tuple[Aspect, re.Pattern[str]]] | None = None
_DEFAULT_PROVIDER = RobustSemanticLoader(strategy=SemanticLoadStrategy.YAML_ONLY)
_ASPECT_MAP = {
    "price": Aspect.PRICE,
    "quality": Aspect.QUALITY,
    "function": Aspect.FUNCTION,
    "service": Aspect.SERVICE,
    "ux": Aspect.UX,
}


def _load_unified_lexicon() -> None:
    """从配置路径加载词库用于可选匹配，不依赖数据库。"""
    global _LEX_FEATURE_PATS, _LEX_PAIN_PATS
    if _LEX_FEATURE_PATS is not None and _LEX_PAIN_PATS is not None:
        return
    try:
        cfg_path = os.getenv(
            "SEMANTIC_LEXICON_PATH",
            "backend/config/semantic_sets/unified_lexicon.yml",
        )
        lex = UnifiedLexicon(Path(cfg_path))
        feats = lex.get_features()
        pains = lex.get_pain_points()
        _LEX_FEATURE_PATS = lex.get_patterns_for_matching(feats)
        _LEX_PAIN_PATS = lex.get_patterns_for_matching(pains)
    except Exception:
        _LEX_FEATURE_PATS, _LEX_PAIN_PATS = [], []


def _load_expanded_pain_lexicon() -> None:
    """加载通用痛点词典（expanded_pain.yml），构建正则模式。"""
    global _EXPANDED_PAIN_PATS
    if _EXPANDED_PAIN_PATS is not None:
        return
    try:
        cfg_path = os.getenv(
            "EXPANDED_PAIN_LEXICON_PATH",
            "backend/config/semantic_sets/expanded_pain.yml",
        )
        p = Path(cfg_path)
        if not p.exists():
            _EXPANDED_PAIN_PATS = []
            return
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        categories = data.get("pain_categories") or {}
        pats: list[Tuple[Aspect, re.Pattern[str]]] = []

        def _compile(items: List[str]) -> List[re.Pattern[str]]:
            out: list[re.Pattern[str]] = []
            for it in items:
                s = (it or "").strip()
                if not s:
                    continue
                esc = re.escape(s)
                if re.search(r"[A-Za-z]", s):
                    pat = re.compile(rf"\b{esc}\b", re.IGNORECASE)
                else:
                    pat = re.compile(esc, re.IGNORECASE)
                out.append(pat)
            return out

        for cat, cfg in categories.items():
            kws = cfg.get("keywords") if isinstance(cfg, dict) else None
            if not kws:
                continue
            aspect = _ASPECT_MAP.get(cat, Aspect.OTHER)
            for pat in _compile(list(kws)):
                pats.append((aspect, pat))
        _EXPANDED_PAIN_PATS = pats
    except Exception:
        _EXPANDED_PAIN_PATS = []


@dataclass(slots=True)
class Classification:
    category: Category
    aspect: Aspect
    sentiment_score: float = 0.0
    sentiment_label: str = "neutral"


def classify_category_aspect(text: str) -> Classification:
    """轻量规则：关键词 + 可选统一词表。"""
    t = (text or "").lower()

    # 动态加载 Aspect 词典（痛点/场景关键词）
    _load_aspect_keywords()

    # Bot Filter: Early exit
    bot_patterns = [
        r"i am a bot",
        r"performed automatically",
        r"contact the moderators",
        r"submission has been removed",
        r"automatically removed",
        r"bot action",
    ]
    if any(re.search(p, t) for p in bot_patterns):
        return Classification(category=Category.OTHER, aspect=Aspect.OTHER)

    matched_aspect: Aspect | None = None
    # 优先：物流强制触发（防止 service 抢占）
    shipping_triggers = (
        ("package",),
        ("fedex",),
        ("dhl",),
        ("usps",),
        ("parcel",),
    )
    if any(all(token in t for token in combo) for combo in shipping_triggers) and (
        "lost" in t or "delayed" in t or "damage" in t or "stuck" in t or "tracking" in t
    ):
        matched_aspect = Aspect.SHIPPING
    # 优先：配置文件映射（优先级顺序，避免 service 抢占 shipping）
    aspect_priority = [
        Aspect.SHIPPING,
        Aspect.QUALITY,
        Aspect.SERVICE,
        Aspect.FUNCTION,
        Aspect.UX,
        Aspect.RETURN,
        Aspect.SUB_CANCEL,
        Aspect.SUB_HIDDEN_FEE,
        Aspect.SUB_AUTO_RENEW,
        Aspect.SUB_PRICE,
        Aspect.SCAM,
        Aspect.SUBSCRIPTION,  # 兜底
        Aspect.CONTENT,
        Aspect.INSTALL,
        Aspect.ECOSYSTEM,
        Aspect.STRENGTH,
    ]
    if matched_aspect is None:
        for asp in aspect_priority:
            pats = _ASPECT_KEYWORD_PATS.get(asp.value, [])
            if any(pat.search(t) for pat in pats):
                matched_aspect = asp
                break

    # 扩展痛点词典（仅在未匹配时使用）
    if matched_aspect is None:
        try:
            _load_expanded_pain_lexicon()
            for asp, pat in (_EXPANDED_PAIN_PATS or []):
                if pat.search(t):
                    matched_aspect = asp
                    break
        except Exception:
            pass  # 保持 matched_aspect 不变

    if any(k in t for k in SOLUTION_KWS):
        category = Category.SOLUTION
    elif matched_aspect:
        # If aspect detected, trust it as Pain (or relevant context)
        category = Category.PAIN
    elif any(k in t for k in STRONG_PAIN_KWS):
         # Strong sentiment w/o aspect -> Generic Pain
        category = Category.PAIN
    elif any(k in t for k in SUBS_KWS):
        category = Category.PAIN
    elif any(k in t for k in WEAK_PAIN_KWS):
        # Weak pain w/o aspect -> Noise/Question -> OTHER
        category = Category.OTHER
    else:
        category = Category.OTHER

    # 可选：统一词表辅助
    try:
        _load_unified_lexicon()
        if category == Category.OTHER:
             if any(pat.search(t) for _, pat in (_LEX_PAIN_PATS or [])):
                 category = Category.PAIN
             elif any(pat.search(t) for _, pat in (_LEX_FEATURE_PATS or [])):
                 category = Category.SOLUTION
    except Exception:
        pass

    def _match_list(keywords) -> bool:
        for kw in keywords:
            kw = (kw or "").strip()
            if not kw:
                continue
            esc = re.escape(kw)
            if re.search(r"[A-Za-z0-9]", kw):
                esc = esc.replace(r"\ ", r"\s+")
                pat = re.compile(rf"\b{esc}\b", re.IGNORECASE)
            else:
                pat = re.compile(esc, re.IGNORECASE)
            if pat.search(t):
                return True
        return False

    if matched_aspect is not None:
        aspect = matched_aspect
    elif _match_list(SUBS_KWS):
        aspect = Aspect.SUBSCRIPTION
    elif _match_list(PRICE_KWS):
        aspect = Aspect.PRICE
    elif _match_list(_ASPECT_KEYWORDS.get("sub_cancel", [])):
        aspect = Aspect.SUB_CANCEL
    elif _match_list(_ASPECT_KEYWORDS.get("sub_hidden_fee", [])):
        aspect = Aspect.SUB_HIDDEN_FEE
    elif _match_list(_ASPECT_KEYWORDS.get("sub_auto_renew", [])):
        aspect = Aspect.SUB_AUTO_RENEW
    elif _match_list(_ASPECT_KEYWORDS.get("sub_price", [])):
        aspect = Aspect.SUB_PRICE
    elif _match_list(QUALITY_KWS):
        aspect = Aspect.QUALITY
    elif _match_list(SHIPPING_KWS):
        aspect = Aspect.SHIPPING
    elif _match_list(SERVICE_KWS):
        aspect = Aspect.SERVICE
    elif _match_list(FUNCTION_KWS):
        aspect = Aspect.FUNCTION
    elif _match_list(UX_KWS):
        aspect = Aspect.UX
    elif _match_list(INSTALL_KWS):
        aspect = Aspect.INSTALL
    elif _match_list(ECO_KWS):
        aspect = Aspect.ECOSYSTEM
    elif _match_list(STRENGTH_KWS):
        aspect = Aspect.STRENGTH
    elif _match_list(CONTENT_KWS):
        aspect = Aspect.CONTENT
    elif _match_list(RETURN_KWS):
        aspect = Aspect.RETURN
    else:
        aspect = Aspect.OTHER

    # Sentiment Analysis
    vs = _vader.polarity_scores(t)
    compound = vs.get("compound", 0.0)
    
    label = "neutral"
    if compound >= 0.05:
        label = "positive"
    elif compound <= -0.05:
        label = "negative"

    return Classification(
        category=category, 
        aspect=aspect,
        sentiment_score=compound,
        sentiment_label=label
    )


class TextClassifier:
    """注入式分类器，依赖 SemanticProvider。"""

    def __init__(self, semantic_provider: SemanticProvider | None = None) -> None:
        self._provider = semantic_provider or _DEFAULT_PROVIDER

    async def classify(self, text: str) -> Classification:
        try:
            await self._provider.load()
        except Exception:
            # 语义加载失败时仍返回规则判断
            pass
        return classify_category_aspect(text)
