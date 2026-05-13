# Phase 93 - Update post_scores_latest_v view

## Action
- Checked view presence via SQL (`to_regclass` + row count).
- Ran `make -f makefiles/db.mk db-upgrade BACKEND_DIR=backend` to apply latest Alembic view definitions.
- Rechecked view availability after upgrade.

## Result
- `post_scores_latest_v` present; rows: 195985.
- Chrome DevTools MCP unavailable (profile already in use), verification skipped.
