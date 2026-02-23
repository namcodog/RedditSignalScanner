# phase172 - inline structured report fallback + live task check

## Scope
- Provide inline LLM fallback for report_structured when missing.
- Verify real report_structured output on a fresh task.

## Findings
- Existing task `0c3bccf5-dd2c-4ca1-96ec-c3035cc21eac` returns `report_structured` as null.
- New task `5d5991a1-1617-4513-80e3-69b6408ff517` returns non-empty `report_structured` with 5 sections.
- LLM settings are present in `.env` (LLM_MODEL_NAME, OPENAI_BASE, OPENROUTER_API_KEY, ENABLE_LLM_SUMMARY).

## Changes
- ReportService now attempts inline LLM generation for `report_structured` when missing and `ENABLE_REPORT_INLINE_LLM=true`.
- Added JSON extraction helper to ReportService.
- Added unit test for inline structured report generation.

## Tests
- pytest backend/tests/services/test_report_service_market_mode.py -k "structured_report_inline" -q
  - Result: PASS (1 test)
  - Warning: PytestConfigWarning asyncio_default_fixture_loop_scope

## Notes
- Inline generation is gated by `ENABLE_REPORT_INLINE_LLM` to avoid blocking `/api/report` by default.
