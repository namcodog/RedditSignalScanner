# phase169 - report endpoint llm blocking fix

## Scope
- Remove synchronous LLM enhancements from /api/report to avoid UI blocking.
- Support .env.local loading for local test credentials.

## Changes
- Added .env.local load precedence for both repo root and backend folders.
- Added enable_report_inline_llm setting (default false) to gate report-stage LLM.
- Gated LLM normalizer / evidence summarizer / title+slogan / T1 market report behind enable_report_inline_llm.

## Files touched
- backend/app/core/config.py
- backend/app/services/report_service.py

## Notes
- LLM is now used only in analysis stage for report_html generation unless ENABLE_REPORT_INLINE_LLM=1.
