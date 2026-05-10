# Community Governance Rules

Date: 2026-05-07

Status: historical governance contract. For current Community Intelligence product decisions, use `docs/reference/community-intelligence-clean-contract-2026-05-07.md`.

This file records how Phase 0 / 1 / 2 audited and prepared community-pool data. It must not be used to claim the community recommendation product is complete, to treat `community_pool` as the recommendation surface, or to downgrade old DB communities only because Hotpost did not publish cards from them.

2026-05-08 archive note: Phase 0 / 1 / 2 governance is now a legacy data-preparation track. It remains useful for history, audit, Dev write traceability, and rollback context, but it is not the current product recommendation chain. Current product direction is defined by `docs/reference/community-intelligence-clean-contract-2026-05-07.md` and `docs/reference/community-discovery-legacy-archive-2026-05-08.md`.

## Phase 0 Scope

Phase 0 is a read-only governance audit. It does not recommend communities to users.

Corrected operating interpretation:
- "Enter community_pool" means the community is allowed into the system learning scope.
- It does not mean high-frequency crawl, high weight, or automatic publishing.
- Generic communities can enter the pool, but must be usage-capped so they do not crowd out long-tail communities.
- Generic communities also have a hot-floor rule: must-have platform hot signals must be covered even when regular generic learning budget is full.
- The generic cap applies to regular learning budget only. A cap bypass must be explicit and use `must_have_hot_signal`.
- Long-tail communities should be judged by activity, post quality, vertical density, and learnability, not by Hotpost card count alone.
- `stale_review` means old pool assets awaiting re-check; it is not deletion or downgrade evidence.

Allowed reads:
- Hotpost published cards
- `community_pool`
- `discovered_communities`
- `backend/config/hotpost_supply_discovery_v2.yaml`

Not allowed:
- DB writes
- New tables
- Reddit live search
- API or frontend changes
- `hotpost-mini` changes
- Recommendation algorithm claims

## Governance States

### promote_candidate

A community is a promote candidate when Hotpost has already produced useful published cards from it, but it is missing from active `community_pool`.

Minimum evidence:
- `hotpost_card_count >= 2`, or
- `hotpost_card_count >= 1` and the community is already in supply config or `discovered_communities`.

Promotion bands:
- `strong`: `hotpost_card_count >= 5` and present in supply config.
- `medium`: `hotpost_card_count >= 2` and present in supply config.
- `weak`: all other promote candidates, especially Hotpost-only surprise hits not present in supply config.

These bands are evidence-density labels only. They must not be used as a Phase 0 entry gate. Current Phase 0 treats all `promote_candidate` communities as existing-evidence communities for governance review.

### keep_active

A community should stay active when it exists in `community_pool` and has recent Hotpost evidence or strong configured coverage.

Minimum evidence:
- active in `community_pool`, and
- `hotpost_card_count > 0` or present in supply config.

### needs_evidence

A community needs evidence when it appears in supply config or `discovered_communities`, but Hotpost has not yet produced published cards from it. This includes communities that already exist in `community_pool` but are still pending in `discovered_communities`.

### stale_review

A community needs stale review when it is active in `community_pool`, but has no Hotpost cards, no supply config coverage, and no active `discovered_communities` status.

This state does not mean the community is useless or should be deleted. It only means Hotpost has not validated it yet. Before any downgrade, check legacy DB evidence such as posts, comments, labels, historical reports, and old analysis usage.

First-pass review should exclude obvious non-business legacy assets into a low-priority bucket. This is a review convenience, not a DB mutation and not deletion.

### observation_queue

An observation queue community has weak evidence or no current governance source yet.

This is not a global blacklist, not a deletion queue, and not a judgment that the community is low quality. It means Phase 0 has not gathered enough evidence to make it part of the first governance subject.

Examples:
- one Hotpost card, but no supply config, no discovery status, and no pool record
- unclear business ownership
- potentially valuable long-tail community that needs activity and post-quality evidence

## Business Audit Slices

Phase 0 keeps three slices for coverage only:
- pet-products
- ai-tools
- crossborder-ecommerce

These are not recommendation fixtures. They are audit slices used to detect missing coverage and categorization errors.

When a business slice surfaces an unrelated community, call it a classification error or cross-domain mismatch. Do not call it "slice noise"; the issue is wrong categorization, not the slice itself.

## Phase 1 Generic Community Budget

Generic communities are valuable because they surface the hottest platform-level discussions. They are also broad enough to crowd out long-tail learning if left uncapped.

Phase 1 therefore uses two rules:

- Regular learning cap: generic communities default to `25%` of learning budget.
- Human-review ceiling: generic communities can temporarily reach `30%`; above that requires explicit human review.
- Hot floor: must-have hot signals from generic communities bypass the regular cap.
- Bypass reason: every cap bypass must record `must_have_hot_signal`.
- Scope limit: hot-floor bypass covers the hot signal only; it must not silently raise long-term learning weight.

## Phase 1 Deferrals

- Add `CommunityDiscoveryService` dry-run mode.
- Decide whether to reuse `community_ranker.compute_ranking_scores`.
- Add semantic relevance or embedding-based matching.
- Decide whether governance results need durable snapshots.
