# Reddit Signal Scanner Constitution

## Core Principles

### I. PRD-Driven Development (NON-NEGOTIABLE)
**All implementation must trace back to explicit PRD requirements**
- Every feature, API, and data model must reference a specific PRD document
- No code without PRD: If a requirement is missing, update the PRD first, then implement
- PRD-INDEX.md is the single source of truth for feature dependencies and implementation order
- Changes to requirements must be documented in PRD before code changes

### II. Type Safety Zero Tolerance
**100% type safety with mypy --strict**
- No `# type: ignore` comments allowed
- No `Any` types except in explicitly documented edge cases
- All functions must have complete type annotations
- Pydantic models for all data validation and serialization
- Type checking must pass before any commit

### III. Test-First Development (NON-NEGOTIABLE)
**TDD mandatory: Tests written → User approved → Tests fail → Then implement**
- Unit tests for all services and utilities
- Integration tests for API endpoints
- End-to-end tests for complete user journeys
- Test coverage: Backend >80%, Frontend >70%
- All tests must pass before merge

### IV. Four Questions Framework
**All phase deliverables must answer these questions:**
1. 通过深度分析发现了什么问题？根因是什么？
2. 是否已经精确的定位到问题？
3. 精确修复问题的方法是什么？
4. 下一步的事项要完成什么？

### V. Quality Gates
**Every phase must meet quality standards before proceeding**
- mypy --strict: 0 errors
- pytest: 100% pass rate
- Code review: Required for all changes
- Documentation: Updated with code changes
- Performance: Meet PRD-specified targets

### VI. Linus Design Philosophy
**Simple, honest architecture over clever solutions**
- Data structures first: Design the 4-table architecture, code follows naturally
- Simple over clever: 4 API endpoints vs 59 routes
- Honest architecture: "5-minute promise" based on cache, not magic
- Eliminate special cases through good data design

## Technology Stack & Compliance

### Reddit API Compliance (CRITICAL)
- ✅ OAuth2 authentication required
- ✅ Respect 60 requests/minute limit (HARD LIMIT)
- ✅ Proper User-Agent: "RedditSignalScanner/1.0"
- ✅ Cache data for performance (合规)
- ✅ Respect user deletion requests
- ✅ No data resale
- ⚠️ Monitor API calls: Alert at 55/min, throttle at 58/min

### Backend Stack
- Python 3.11+, FastAPI (async), PostgreSQL + asyncpg
- SQLAlchemy 2.0 (async), Celery + Redis, Alembic
- Testing: pytest, pytest-asyncio

### Frontend Stack
- TypeScript, React 18+, Vite
- Testing: Vitest, React Testing Library

## Development Workflow

### Phase Execution
1. Planning: Review PRD, create implementation plan
2. Schema Workshop: Lock down data models and API contracts
3. Implementation: Follow TDD, maintain type safety
4. Testing: Unit → Integration → E2E
5. Review: Code review + PRD compliance check
6. Documentation: Update docs, ADRs, and phase logs

### Daily Quality Check
```bash
make quick-gate-local  # Must pass before end of day
```

## Performance Standards

- POST /api/analyze: < 200ms
- Analysis time: < 5 minutes (90% cache hit)
- Cache hit rate: > 90%
- Concurrent users: 100 users, 95% success rate
- Memory: < 2GB per worker, CPU: < 90%

## Governance

### Constitution Authority
- This constitution supersedes all other development practices
- Amendments require: Documentation → Review → Approval → Migration plan
- All PRs must verify compliance with constitution

### Phase Gate Requirements
- Each phase must produce deliverables in `reports/phase-log/`
- Phase cannot proceed without Lead approval
- Quality gates must be met (defined in `docs/2025-10-10-质量标准与门禁规范.md`)

**Version**: 1.0.0 | **Ratified**: 2025-10-15 | **Last Amended**: 2025-10-15