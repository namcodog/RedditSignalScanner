# Phase 1 Community Pool Dry-Run

- DB writes: `false`
- existing_evidence_communities: `108`
- proposed_pool_additions: `69`
- keep_pool_unchanged: `39`
- generic_cap_required: `27`
- review_only: `needs_evidence=31 / stale_review=115 / observation_queue=10`

## Generic Community Budget

- regular_learning_cap_ratio: `25%`
- max_cap_ratio_without_human_review: `30%`
- current_generic_ratio: `25%`
- hot_floor: `enabled`
- allowed_cap_bypass_reason: `must_have_hot_signal`
- must-have hot signals bypass the regular generic cap, but only for hot signal coverage.

## Existing Evidence Rows

| Community | Source State | Phase 1 Action | Role | Cap | Cards |
|---|---|---|---|---|---:|
| r/PPC | promote_candidate | propose_pool_addition | generic_hotspot | Y | 37 |
| r/DigitalMarketing | promote_candidate | propose_pool_addition | generic_hotspot | Y | 33 |
| r/ClaudeCode | promote_candidate | propose_pool_addition | ai_workflow | N | 30 |
| r/OpenAI | promote_candidate | propose_pool_addition | generic_hotspot | Y | 30 |
| r/ClaudeAI | promote_candidate | propose_pool_addition | generic_hotspot | Y | 23 |
| r/GiftIdeas | promote_candidate | propose_pool_addition | longtail_vertical | N | 21 |
| r/ManyBaggers | promote_candidate | propose_pool_addition | longtail_vertical | N | 20 |
| r/artificial | promote_candidate | propose_pool_addition | generic_hotspot | Y | 18 |
| r/kickstarter | promote_candidate | propose_pool_addition | longtail_vertical | N | 18 |
| r/ProductManagement | promote_candidate | propose_pool_addition | generic_hotspot | Y | 17 |
| r/EDC | promote_candidate | propose_pool_addition | longtail_vertical | N | 14 |
| r/AI_Agents | promote_candidate | propose_pool_addition | ai_workflow | N | 11 |
| r/LLM | promote_candidate | propose_pool_addition | ai_workflow | N | 10 |
| r/analytics | promote_candidate | propose_pool_addition | generic_hotspot | Y | 9 |
| r/Google_Ads | promote_candidate | propose_pool_addition | generic_hotspot | Y | 9 |
| r/googleads | promote_candidate | propose_pool_addition | generic_hotspot | Y | 9 |
| r/adops | promote_candidate | propose_pool_addition | generic_hotspot | Y | 8 |
| r/CampingGear | promote_candidate | propose_pool_addition | longtail_vertical | N | 6 |
| r/projectmanagement | promote_candidate | propose_pool_addition | generic_hotspot | Y | 6 |
| r/AsianBeauty | promote_candidate | propose_pool_addition | longtail_vertical | N | 5 |
| r/content_marketing | promote_candidate | propose_pool_addition | generic_hotspot | Y | 5 |
| r/cursor | promote_candidate | propose_pool_addition | ai_workflow | N | 5 |
| r/juststart | promote_candidate | propose_pool_addition | generic_hotspot | Y | 5 |
| r/productivity | promote_candidate | propose_pool_addition | generic_hotspot | Y | 5 |
| r/EntrepreneurRideAlong | promote_candidate | propose_pool_addition | longtail_vertical | N | 4 |
| r/ExperiencedDevs | promote_candidate | propose_pool_addition | longtail_vertical | N | 4 |
| r/MachineLearning | promote_candidate | propose_pool_addition | longtail_vertical | N | 4 |
| r/stationery | promote_candidate | propose_pool_addition | longtail_vertical | N | 4 |
| r/b2bmarketing | promote_candidate | propose_pool_addition | platform_ops | N | 3 |
| r/codex | promote_candidate | propose_pool_addition | longtail_vertical | N | 3 |
| r/managers | promote_candidate | propose_pool_addition | longtail_vertical | N | 3 |
| r/Notion | promote_candidate | propose_pool_addition | longtail_vertical | N | 3 |
| r/sales | promote_candidate | propose_pool_addition | platform_ops | N | 3 |
| r/singularity | promote_candidate | propose_pool_addition | generic_hotspot | Y | 3 |
| r/SkincareAddiction | promote_candidate | propose_pool_addition | longtail_vertical | N | 3 |
| r/agi | promote_candidate | propose_pool_addition | longtail_vertical | N | 2 |
| r/beagles | promote_candidate | propose_pool_addition | longtail_vertical | N | 2 |
| r/ChatGPTCoding | promote_candidate | propose_pool_addition | ai_workflow | N | 2 |
| r/claudeskills | promote_candidate | propose_pool_addition | ai_workflow | N | 2 |
| r/ContentCreators | promote_candidate | propose_pool_addition | longtail_vertical | N | 2 |
| r/customersupport | promote_candidate | propose_pool_addition | longtail_vertical | N | 2 |
| r/Emailmarketing | promote_candidate | propose_pool_addition | platform_ops | N | 2 |
| r/helpdesk | promote_candidate | propose_pool_addition | longtail_vertical | N | 2 |
| r/hobonichi | promote_candidate | propose_pool_addition | longtail_vertical | N | 2 |
| r/OpenWebUI | promote_candidate | propose_pool_addition | ai_workflow | N | 2 |
| r/perplexity_ai | promote_candidate | propose_pool_addition | longtail_vertical | N | 2 |
| r/PKMS | promote_candidate | propose_pool_addition | longtail_vertical | N | 2 |
| r/programming | promote_candidate | propose_pool_addition | longtail_vertical | N | 2 |
| r/research | promote_candidate | propose_pool_addition | longtail_vertical | N | 2 |
| r/revops | promote_candidate | propose_pool_addition | longtail_vertical | N | 2 |
| r/seogrowth | promote_candidate | propose_pool_addition | generic_hotspot | Y | 2 |
| r/Substack | promote_candidate | propose_pool_addition | generic_hotspot | Y | 2 |
| r/sysadmin | promote_candidate | propose_pool_addition | longtail_vertical | N | 2 |
| r/vibecoding | promote_candidate | propose_pool_addition | ai_workflow | N | 2 |
| r/writing | promote_candidate | propose_pool_addition | longtail_vertical | N | 2 |
| r/ApartmentHacks | promote_candidate | propose_pool_addition | longtail_vertical | N | 1 |
| r/AskMarketing | promote_candidate | propose_pool_addition | platform_ops | N | 1 |
| r/Blogging | promote_candidate | propose_pool_addition | longtail_vertical | N | 1 |
| r/claude | promote_candidate | propose_pool_addition | ai_workflow | N | 1 |
| r/comfyui | promote_candidate | propose_pool_addition | ai_workflow | N | 1 |
| r/consulting | promote_candidate | propose_pool_addition | longtail_vertical | N | 1 |
| r/fountainpens | promote_candidate | propose_pool_addition | longtail_vertical | N | 1 |
| r/homeoffice | promote_candidate | propose_pool_addition | longtail_vertical | N | 1 |
| r/Journaling | promote_candidate | propose_pool_addition | longtail_vertical | N | 1 |
| r/NewParents | promote_candidate | propose_pool_addition | longtail_vertical | N | 1 |
| r/ObsidianMD | promote_candidate | propose_pool_addition | longtail_vertical | N | 1 |
| r/OpenSourceAI | promote_candidate | propose_pool_addition | longtail_vertical | N | 1 |
| r/planners | promote_candidate | propose_pool_addition | longtail_vertical | N | 1 |
| r/sidehustle | promote_candidate | propose_pool_addition | longtail_vertical | N | 1 |
| r/BuyItForLife | keep_active | keep_pool_unchanged | longtail_vertical | N | 51 |
| r/ecommerce | keep_active | keep_pool_unchanged | longtail_vertical | N | 37 |
| r/FacebookAds | keep_active | keep_pool_unchanged | generic_hotspot | Y | 34 |
| r/FulfillmentByAmazon | keep_active | keep_pool_unchanged | platform_ops | N | 28 |
| r/SEO | keep_active | keep_pool_unchanged | generic_hotspot | Y | 27 |
| r/CleaningTips | keep_active | keep_pool_unchanged | longtail_vertical | N | 14 |
| r/EtsySellers | keep_active | keep_pool_unchanged | platform_ops | N | 14 |
| r/Frugal | keep_active | keep_pool_unchanged | longtail_vertical | N | 14 |
| r/LocalLLaMA | keep_active | keep_pool_unchanged | longtail_vertical | N | 12 |
| r/AmazonSeller | keep_active | keep_pool_unchanged | platform_ops | N | 11 |
| r/ChatGPT | keep_active | keep_pool_unchanged | generic_hotspot | Y | 11 |
| r/espresso | keep_active | keep_pool_unchanged | longtail_vertical | N | 11 |
| r/shopify | keep_active | keep_pool_unchanged | platform_ops | N | 11 |
| r/dogs | keep_active | keep_pool_unchanged | longtail_vertical | N | 10 |
| r/Entrepreneur | keep_active | keep_pool_unchanged | generic_hotspot | Y | 9 |
| r/flashlight | keep_active | keep_pool_unchanged | longtail_vertical | N | 9 |
| r/onebag | keep_active | keep_pool_unchanged | longtail_vertical | N | 9 |
| r/PromptEngineering | keep_active | keep_pool_unchanged | longtail_vertical | N | 8 |
| r/TechSEO | keep_active | keep_pool_unchanged | generic_hotspot | Y | 7 |
| r/automation | keep_active | keep_pool_unchanged | longtail_vertical | N | 5 |
| r/smallbusiness | keep_active | keep_pool_unchanged | generic_hotspot | Y | 5 |
| r/beyondthebump | keep_active | keep_pool_unchanged | longtail_vertical | N | 3 |
| r/knives | keep_active | keep_pool_unchanged | longtail_vertical | N | 3 |
| r/SaaS | keep_active | keep_pool_unchanged | generic_hotspot | Y | 3 |
| r/startups | keep_active | keep_pool_unchanged | generic_hotspot | Y | 3 |
| r/3Dprinting | keep_active | keep_pool_unchanged | longtail_vertical | N | 2 |
| r/DIY | keep_active | keep_pool_unchanged | longtail_vertical | N | 2 |
| r/homeowners | keep_active | keep_pool_unchanged | longtail_vertical | N | 2 |
| r/marketing | keep_active | keep_pool_unchanged | generic_hotspot | Y | 2 |
| r/Ultralight | keep_active | keep_pool_unchanged | longtail_vertical | N | 2 |
| r/AutoDetailing | keep_active | keep_pool_unchanged | longtail_vertical | N | 1 |
| r/backpacking | keep_active | keep_pool_unchanged | longtail_vertical | N | 1 |
| r/bigseo | keep_active | keep_pool_unchanged | generic_hotspot | Y | 1 |
| r/Coffee | keep_active | keep_pool_unchanged | longtail_vertical | N | 1 |
| r/Justrolledintotheshop | keep_active | keep_pool_unchanged | longtail_vertical | N | 1 |
| r/StableDiffusion | keep_active | keep_pool_unchanged | longtail_vertical | N | 1 |
| r/battlestations | keep_active | keep_pool_unchanged | longtail_vertical | N | 0 |
| r/bushcraft | keep_active | keep_pool_unchanged | longtail_vertical | N | 0 |
| r/survival | keep_active | keep_pool_unchanged | longtail_vertical | N | 0 |

## Write Gate

This report is a dry-run gate. It does not authorize DB writes.
A later write step needs explicit human approval and a row-level rollback plan.
- would_insert_pool_rows: `69`
- would_update_pool_rows: `0`
- fields_requiring_future_approval: `community, source_state, role, cap_required, suggested_usage_policy, required_evidence_fields, evidence_snapshot`
