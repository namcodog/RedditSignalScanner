# phase170 - dev db A_full task sampling + UI E2E smoke

## Scope
- Find A_full tasks in dev DB for homepage examples.
- Verify UI report rendering with authenticated user.
- Create fixed QA credentials in local env (not in repo).

## Actions
- Queried dev DB: facts_run_logs summary for report_tier=A_full.
- Created QA pro user via /api/auth/register and stored creds in .env.local.
- Ran 3 analyze tasks under QA user (lab/gold) to test tiers.
- Aligned task ownership for A_full sample tasks to a single QA user.
- Started backend on :8006 (dev DB) and frontend on :3006 with /api proxy.
- Ran Playwright smoke: login -> /report/{task_id} -> dimension detail.

## Findings
- Dev DB has only 1 unique A_full product description; 3 A_full tasks exist but same domain.
- New QA tasks for other domains downgraded (X_blocked / C_scouting) due to topic_mismatch/pains_low.
- UI report renders with data for A_full task when logged in as owner; pain points and drivers show content.

## Data changes (dev only)
- QA pro user created: qa_pro_dev@example.com (password stored in .env.local).
- QA A_full user password reset to known value (see .env.local).
- Task ownership updated for sample A_full tasks to a single QA user.

## Sample A_full task_ids (dev)
- 6fb4538c-941e-4b03-bcba-29b54ffeaa8d
- d2dc7253-5ba7-4424-81bc-cbaeb5dc0da3
- 0c3bccf5-dd2c-4ca1-96ec-c3035cc21eac

## UI smoke
- Login ok on http://localhost:3006 with QA A_full user.
- /report/0c3bccf5-dd2c-4ca1-96ec-c3035cc21eac loads; cards and detail panels show data.

## Next
- If 3 distinct domains are required, run new analyses after expanding community_pool or adjust topic profiles.
- Add homepage sample cards using the above task_ids (single owner).
