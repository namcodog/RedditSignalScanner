from __future__ import annotations


GROWTH_TOPIC_PACKS = [
    {
        "topic_pack_id": "paid-economics",
        "title": "投放经济",
        "description": "ROI、ROAS、Ads、投流效率、CAC。",
        "target_share": 35,
        "subreddits": ["PPC", "FacebookAds", "googleads", "Google_Ads", "adops"],
        "keywords": {
            "category": ["blended cac", "channel profitability", "incrementality test", "offline conversion import", "paid search profitability"],
            "problem": ["over reliant on paid ads", "platform roas vs blended roas", "attribution gap", "search partners wasting budget", "scale and lower roas"],
            "change": ["cutting paid spend what happened", "moved budget off meta", "what is still profitable in paid social", "when to lower roas target", "budget reallocation after cpc spike"],
        },
    },
    {
        "topic_pack_id": "organic-discovery",
        "title": "自然增长",
        "description": "SEO、GEO、搜索、内容分发、自然流量。",
        "target_share": 30,
        "subreddits": ["SEO", "bigseo", "content_marketing", "Entrepreneur"],
        "keywords": {
            "category": ["seo", "geo", "organic traffic", "search visibility", "content distribution"],
            "problem": ["ranking drop", "indexing", "traffic decay", "search intent"],
            "change": ["google update", "search shift", "what ranks", "discovery trend"],
        },
    },
    {
        "topic_pack_id": "funnel-conversion",
        "title": "转化链路",
        "description": "独立站、落地页、checkout、流量转化。",
        "target_share": 35,
        "subreddits": ["ecommerce", "shopify", "SaaS", "marketing", "smallbusiness"],
        "keywords": {
            "category": ["landing page", "checkout", "conversion rate", "site conversion", "funnel"],
            "problem": ["drop-off", "bounce", "lead quality", "form friction", "cart abandonment"],
            "change": ["go to market", "playbook", "what converts", "offer test"],
        },
    },
]
