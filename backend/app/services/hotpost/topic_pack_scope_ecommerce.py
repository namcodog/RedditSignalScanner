from __future__ import annotations


ECOMMERCE_TOPIC_PACKS = [
    {
        "topic_pack_id": "selection-signals",
        "title": "选品信号",
        "description": "需求缺口、品类机会、值得继续追的细分产品信号。",
        "target_share": 60,
        "subreddits": ["BuyItForLife", "Coffee", "espresso", "CampingGear", "EDC", "homeowners", "dogs", "gadgets"],
        "keywords": {
            "category": [
                "dog travel accessory",
                "pet hair remover tool",
                "espresso machine for small kitchen",
                "coffee grinder apartment setup",
                "camping gear for beginners",
                "edc organizer pouch",
                "small space storage product",
                "desk cable management product",
            ],
            "problem": [
                "wish this existed",
                "can't find a better one",
                "worth buying for small space",
                "good for travel setup",
                "durable everyday carry",
                "best option for pet owners",
            ],
            "change": ["better alternative", "new favorite product", "switched to this", "product trend", "buy it for life"],
        },
    },
    {
        "topic_pack_id": "category-winds",
        "title": "类目风向",
        "description": "类目热度、市场拥挤度、需求风向变化。",
        "target_share": 25,
        "subreddits": ["AmazonSeller", "FulfillmentByAmazon", "EtsySellers", "EntrepreneurRideAlong", "sidehustle"],
        "keywords": {
            "category": [
                "what category is growing",
                "seasonal demand shift ecommerce",
                "amazon niche trend",
                "etsy category trend",
            ],
            "problem": [
                "saturated niche amazon",
                "too competitive category",
                "niche getting crowded",
                "inventory risk in this niche",
            ],
            "change": [
                "what niche still has room",
                "demand shift ecommerce",
                "category getting crowded",
                "what category are you avoiding",
            ],
        },
    },
    {
        "topic_pack_id": "kill-signals",
        "title": "否决信号",
        "description": "运费、仲裁、平台、单位经济等高约束信号。",
        "target_share": 15,
        "subreddits": ["AmazonSeller", "FulfillmentByAmazon", "shopify", "ecommerce"],
        "keywords": {
            "category": ["fulfillment cost", "platform risk", "unit economics ecommerce", "return rate problem"],
            "problem": ["margin squeeze", "chargeback issue", "refund abuse", "ppc not profitable", "conversion dropping"],
            "change": ["policy change", "fee increase", "profit squeeze", "shipping cost jump"],
        },
    },
]
