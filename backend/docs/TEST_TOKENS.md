# Day 5 Test Token Guide

Backend A provides a helper script so the frontend team can authenticate
requests during Day 5 without implementing the full signup/login flow.

## 1. Generate Tokens

```bash
cd backend
python scripts/generate_test_token.py
```

The script prints two users:

| Email                       | User ID                                  | Purpose              | Validity |
|----------------------------|------------------------------------------|----------------------|----------|
| `frontend-test@example.com`| `00000000-0000-0000-0000-000000000001`    | 功能联调             | 7 days   |
| `frontend-dev@example.com` | `00000000-0000-0000-0000-000000000002`    | 回归/集成测试        | 7 days   |

> Ensure the corresponding user records exist in the database. If you are
> using fixtures or seed scripts, add these users before invoking API calls.

## 2. Use Tokens in Requests

Add the header below to every API request:

```
Authorization: Bearer <token>
```

Throttled scripts (curl, Thunder Client, REST Client) can store the token as an
environment variable for convenience.

## 3. Regeneration Policy

- Tokens are valid for seven days. Re-run the script to refresh them.
- For production/staging environments always use the real auth flow; these
  tokens are for local Day 5 development only.
- If the JWT secret or algorithm changes, regenerate tokens immediately.

## 4. Verification Checklist

1. Run `python scripts/generate_test_token.py`.
2. Copy the issued token into an `Authorization` header.
3. Call `GET /api/status/{task_id}` with a known task to confirm the token is
   accepted.
4. Share the token values securely (avoid committing them to git).

