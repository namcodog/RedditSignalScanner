# Authentication System Design (Day 5 Baseline)

Status: Prepared on Day 5 to satisfy `PRD/PRD-06-用户认证.md` Phase 1 scope.

---

## 1. Objectives (`PRD-06 §1`)

- Deliver email/password registration and login that finishes within 30 seconds.
- Uphold multi-tenant isolation by requiring `user_id` (`sub`) on every protected API.
- Operate in a stateless manner using JWT access tokens (24h expiry).
- Provide a baseline that unblocks Frontend Day 5 and QA Phase 2.

---

## 2. High-Level Architecture

```
┌─────────────┐      ┌────────────────────────────┐      ┌─────────────────────┐
│  Client UI  │ ─►─► │ /api/auth/register|login   │ ─►─► │ Token (JWT HS256)   │
└────┬────────┘      └─────────┬──────────────────┘      └──────────┬──────────┘
     │                          │                                    │
     │   (Bearer token)         │ write/read                         │ decode & inject
     ▼                          ▼                                    ▼
┌─────────────┐      ┌────────────────────────────┐      ┌─────────────────────┐
│ Protected   │ ◄─◄─ │ SQLAlchemy users table     │ ◄─◄─ │ `decode_jwt_token` │
│ endpoints   │      │ (`app/models/user.py`)     │      │ dependency          │
└─────────────┘      └────────────────────────────┘      └─────────────────────┘
```

Key flows:
1. **Register (`POST /api/auth/register`)**
   - Normalise email, enforce uniqueness (409 on conflict).
   - Hash password via PBKDF2 (`app/core/security.py::hash_password`).
   - Persist `User`, emit JWT with `sub=user.id`, `email`, `iss=settings.app_name`.

2. **Login (`POST /api/auth/login`)**
   - Validate credentials with `verify_password`.
   - Deny inactive accounts (401).
   - Issue fresh token and update `updated_at` audit stamp.

3. **Protected APIs**
   - Depend on `decode_jwt_token` (FastAPI dependency).
   - Verify signature, expiry, and subject.
   - Use `payload.sub` to scope queries (`Task.user_id` filter, etc.).

---

## 3. Data Model (`PRD-06 §2.2`)

| Field      | Source                                 | Notes                                                       |
|------------|----------------------------------------|-------------------------------------------------------------|
| `id`       | `app/models/user.py::User.id`          | UUID primary key, generated server-side                    |
| `email`    | `User.email`                           | Unique (DB + constraint), case-insensitive comparison      |
| `password` | stored as `User.password_hash`         | PBKDF2-SHA256, 100k iterations, 16-byte salt (ASCII-safe)  |
| `is_active`| `User.is_active`                       | Boolean toggle for future suspension flows                 |
| timestamps | `TimestampMixin` (created/updated)     | Timezone-aware, audit support                              |

Additional tenant isolation is derived from `user_id` relationship to domains (`Task.user_id`, `Report.user_id`). No shared tenant table is required for Phase 1 per PRD.

---

## 4. Token Contract (`PRD-06 §2.3`)

Issued by `create_access_token`:

```jsonc
{
  "sub": "UUID string for User.id",
  "email": "user@example.com",
  "iat": 1731244800,
  "exp": 1731331200,
  "iss": "Reddit Signal Scanner"
}
```

- Algorithm: HS256 (`settings.jwt_algorithm`)
- Secret: `settings.jwt_secret` (env-injected), rotate via infra playbooks.
- Lifetime: 24 hours (`timedelta(hours=24)`).
- Response envelope: `AuthTokenResponse` schema (`app/schemas/auth.py`), returning `access_token`, `token_type`, `expires_at`, `user`.

`decode_jwt_token` ensures:
- Signature/issuer validation; rejects malformed payloads.
- Expiry enforcement; returns 401 on expired tokens.
- Optional `tenant_id` for future multi-tenant expansion (kept nullable for Day 5).

### 4.1 Token Refresh & Rotation Plan (`PRD-06 §3.3`)

- **Access token** TTL reduced to 30 minutes starting Day 6 to reduce blast radius of compromised tokens.
- **Refresh token** (JWT, 7-day validity) returned alongside access token once `POST /api/auth/refresh` is delivered (scheduled Day 7). Until then, clients re-authenticate via `/api/auth/login`.
- **Rotation policy**: every refresh operation issues a brand-new refresh token, invalidating the previous value to mitigate replay attacks.
- **Revocation**: refresh token identifiers set to be persisted in Redis for soft-blacklisting after logout (tracked in Day 7 backlog).
- **Client guidance**:
  1. Monitor `expires_at` from `AuthTokenResponse`.
  2. When remaining lifetime <5 minutes, call refresh endpoint (once available).
  3. On refresh failure (401/403), purge local credentials and redirect to login screen.

---

## 5. API Surface (`PRD-06 §3`)

| Endpoint                | Request Schema                 | Response Schema        | Error Handling                        |
|-------------------------|--------------------------------|------------------------|---------------------------------------|
| `POST /api/auth/register` | `RegisterRequest` (email, password ≥8 chars) | `AuthTokenResponse` | 409 duplicate email, 422 validation   |
| `POST /api/auth/login`    | `LoginRequest`                | `AuthTokenResponse`    | 401 bad credentials, 422 validation   |
| `POST /api/auth/refresh`* | `TokenRefreshRequest` (refresh_token) | `AuthTokenResponse` | 401 invalid/expired refresh token     |

> \*Refresh endpoint enters implementation during Day 7. This document records the approved contract so Frontend can prepare interceptors and QA can draft scenarios.

Implementation path: `app/api/routes/auth.py`. Both endpoints share helpers:
- `_normalise_email` trims + lowercases input.
- `_get_user_by_email` performs indexed lookup (`idx_users_email`).
- `_issue_token` wraps token issuance and response assembly.

All responses exclude password hashes and include the nested `AuthUser` payload for convenience on the frontend.

---

## 6. Security Posture (`PRD-06 §4`)

- PBKDF2 hashing with 100k iterations defends against offline attacks (upgrade path to argon2 documented in ADR backlog).
- `secrets.compare_digest` prevents timing leaks during password verification.
- JWT expiry prevents indefinite token reuse; frontend should refresh via login for Day 5.
- Multi-tenant isolation is enforced in downstream routes (`/api/analyze`, `/api/status`, `/api/reports`), returning 403 when `payload.sub` mismatches resource owner.
- Future work (Day 6-8): rate limiting + lockout (`PRD-06 backlog`), refresh tokens, email verification.

---

## 7. Testing Strategy (`PRD-08 §2.1`)

- **Unit Tests**: `backend/tests/core/test_security.py` verifying hash/verify compatibility and token issuance metadata.
- **API Tests**: `backend/tests/api/test_auth.py` covering registration, duplicate email handling (409), login success/failure, and end-to-end token usage against protected endpoints.
- **Integration**: `backend/tests/api/test_auth_integration.py` validates authentication requirements across `/api/analyze` and `/api/status`, including multi-tenant isolation semantics.
- **Future**: once refresh endpoint lands, extend the suite with happy-path + invalid refresh scenarios and add load tests for token rotation.

Test runs execute under `pytest -k auth --maxfail=1`, with async fixtures mirroring existing API test harness.

---

## 8. Operational Notes

- Environment variables: `DATABASE_URL`, `JWT_SECRET`, `JWT_ALGORITHM` (default `HS256`).
- Tokens generated for Frontend smoke tests recorded in `backend/docs/TEST_TOKENS.md`.
- Any schema or behaviour changes must first update `PRD/PRD-06-用户认证.md` before touching implementation, per project doctrine.
- For incident response, keep the token blacklist store in Redis (namespace `auth:revoked`) synced with PRD updates—implementation targeted Day 8.

---

## 9. Frontend Integration Playbook

```typescript
// src/services/httpClient.ts
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth.accessToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Refresh endpoint ships Day 7; before那时 fallback is redirect-to-login.
      window.location.href = '/login';
    }
    return Promise.reject(error);
  },
);

export default api;
```

- Store `accessToken` + `refreshToken` in `localStorage` (or secure store once desktop app planned).
- Tokens are namespaced by tenant ID to support future multi-tenant session switching.
- Once refresh endpoint is live, replace redirect with a call to `POST /api/auth/refresh` and retry the original request transparently.
