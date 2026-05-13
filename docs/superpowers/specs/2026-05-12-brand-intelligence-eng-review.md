# Brand Intelligence Eng Review

Date: 2026-05-12

Status: DONE_WITH_CONCERNS

## Evidence From Current Code

- `content_entities` exists and supports `entity_type='brand'`; it is content-level evidence, not a brand master table.
- `UnifiedLexicon.get_brands()` exists and can support known-brand matching and alias normalization.
- `facts_v2.midstream` has old brand discovery logic, but it is coupled to the old report pipeline and should not be copied directly into Hotpost.
- Hotpost published cards already contain enough evidence fields for a dry-run extractor.
- Miniapp snapshot can carry extra card fields later, but current summary types do not expose brands.

## Architecture Decision

Use a new backend-owned brand intelligence layer:

```text
Published Hotpost cards
        |
        v
Brand candidate extraction
        |
        v
Semantic normalization + evidence checks
        |
        v
Dry-run report
        |
        v
Dev DB write after acceptance
        |
        v
Miniapp/API/report consumers later
```

## Data Model Boundary

```text
brand_registry
  canonical brand asset and lifecycle state

brand_mentions
  evidence rows: where the brand appeared and why it counted

content_entities
  existing post/comment entity mentions; usable as historical supporting evidence

semantic lexicon
  matching rules, aliases, known terms; not the brand master
```

## Minimal Change Set

Target for first implementation:

1. Add a dry-run service under `backend/app/services/brand_intelligence/`.
2. Add a CLI script under `backend/scripts/brand_intelligence/`.
3. Add reports under `reports/brand-intelligence/`.
4. Add tests for extraction, normalization, and report output.

Do not touch frontend, miniapp, Gold DB, or Hotpost publishing flow in R15.0.

## Engineering Concerns

1. False positives
   - Risk: capitalized generic words become brands.
   - Mitigation: first version marks unknown discoveries as `candidate`, requires evidence count and source text, and never auto-verifies.

2. LLM hallucination
   - Risk: model invents brand names from summaries.
   - Mitigation: first version is deterministic and evidence-first. LLM can be introduced later only as a reviewer, not as source of truth.

3. Overloading semantic lexicon
   - Risk: every discovered name becomes a semantic rule.
   - Mitigation: semantic sync is manual or explicitly reviewed after `brand_registry` verification.

4. Polluting Hotpost operations
   - Risk: daily card publishing gets slower or riskier.
   - Mitigation: brand extraction runs after publish as a sidecar report; it must not block V13 publishing or mini snapshot.

5. DB write safety
   - Risk: candidate noise enters permanent tables.
   - Mitigation: R15.0 has no writes; R15.2 writes Dev only with rollback SQL.

## Test Plan

```text
Extraction path
  input: sample published card with known brand evidence
  expect: candidate brand with card_id, community, quote/permalink if available

Normalization path
  input: aliases from semantic lexicon
  expect: same canonical brand key

Noise path
  input: generic capitalized words
  expect: not verified; either absent or candidate with low confidence

Report path
  input: fixture cards
  expect: stable JSON + Markdown summary, no DB writes

DB path, later
  input: accepted brand candidates
  expect: Dev insert only, idempotent rerun, rollback generated
```

## Recommendation

Proceed with R15.0 dry-run first.

Do not create migration before seeing the first report. The schema should be informed by actual evidence fields from Hotpost cards, not imagined fields.
