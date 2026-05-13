# Phase 89 - Limit DB connections per worker

## Action
- Added pool timeout/recycle env support and lowered default async pool limits.
- Updated runtime config to enable pool and cap connections.
- Added tests for pool settings.

## Result
- Tests: `python -m pytest backend/tests/core/test_db_session.py`

## Note
- Chrome DevTools MCP validation not available (browser profile already in use).
