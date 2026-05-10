# phase167 - report data pipeline alignment

## Scope
- Fix backend data completeness for report UI and LLM prompts.

## Changes
- Enriched facts_v2 business_signals with buying_opportunities/competitor_insights/ps_ratio so facts_slice matches prompt V3 expectations.
- Added ps_ratio into facts_slice for LLM consumption.
- Improved example post content extraction (summary/title/selftext/text/body fallback) and r/ prefix normalization; ensured post id lookup works with int/str.
- Added DriverSignal.description and filled it from rationale to support frontend display.
- Added llm_used/llm_model/llm_rounds to analysis sources; metadata now reflects real LLM usage.
- Added OPENROUTER_API_KEY fallback in settings/openai client.

## Files touched
- backend/app/services/analysis_engine.py
- backend/app/services/analysis/insights_enrichment.py
- backend/app/schemas/analysis.py
- backend/app/services/report_service.py
- backend/app/core/config.py
- backend/app/services/llm/clients/openai_client.py

## Verification
- Not run (awaiting user-driven E2E). Focused on data completeness and prompt alignment.

## Notes
- Requires valid OpenRouter credits to produce LLM report_html; otherwise fallback template still used.
