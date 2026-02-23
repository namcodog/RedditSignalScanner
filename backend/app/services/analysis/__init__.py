"""Analysis service submodules offering step-specific helpers."""

from .signal_extraction import (
    BusinessSignals,
    CompetitorSignal,
    OpportunitySignal,
    PainPointSignal,
    SignalExtractor,
)
from .community_discovery import Community, discover_communities
from .keyword_extraction import KeywordExtractionResult, extract_keywords
from .opportunity_scorer import OpportunityScorer
from .pain_cluster import cluster_pain_points
from .competitor_layering import assign_competitor_layers, build_layer_summary
from .scoring_rules import ScoringRulesLoader
from .scoring_templates import TemplateConfigLoader
from .template_matcher import TemplateMatcher
from .text_cleaner import clean_text, score_with_context
from .quote_extractor import QuoteExtractor, QuoteResult

__all__ = [
    "BusinessSignals",
    "CompetitorSignal",
    "Community",
    "KeywordExtractionResult",
    "OpportunitySignal",
    "PainPointSignal",
    "OpportunityScorer",
    "assign_competitor_layers",
    "build_layer_summary",
    "cluster_pain_points",
    "ScoringRulesLoader",
    "TemplateConfigLoader",
    "TemplateMatcher",
    "clean_text",
    "score_with_context",
    "QuoteExtractor",
    "QuoteResult",
    "SignalExtractor",
    "discover_communities",
    "extract_keywords",
]
