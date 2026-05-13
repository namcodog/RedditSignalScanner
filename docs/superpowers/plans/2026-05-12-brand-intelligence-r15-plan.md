# R15 Brand Intelligence Plan

Date: 2026-05-12

## Goal

Build the backend foundation for collecting brands discussed on Reddit inside our current domains.

Plain meaning: the main system owns brand collection and judgment; Hotpost and the miniapp can later consume the result.

## Non Goals

- No miniapp UI in this phase.
- No Gold DB writes.
- No production auto-promotion.
- No hardcoded brand list in Python.
- No brand fields generated directly by card-writing prompts.

## Phase R15.0: Dry-run Brand Report

Step -> validation point:

1. Load published Hotpost cards through shared readers.
   -> Verify no direct JSON bucket rewrite and no publish-chain mutation.

2. Extract brand candidates from card evidence text.
   -> Verify every candidate has at least one evidence object: `card_id`, `community`, `source_text`, and date.

3. Normalize using semantic lexicon brands and aliases.
   -> Verify known aliases collapse to one canonical brand key.

4. Generate reports:
   - `reports/brand-intelligence/brand-digest-YYYY-MM-DD.md`
   - `reports/brand-intelligence/brand-digest-YYYY-MM-DD.json`
   -> Verify report exists, is deterministic, and records `db_writes=false`.

5. Add unit tests for extractor, normalizer, and report writer.
   -> Verify target pytest suite passes.

## Phase R15.0.5: Brand Source Catalog

Step -> validation point:

1. Load all existing brand resources into one read-only source catalog:
   - `backend/config/semantic_sets/unified_lexicon.yml`
   - `backend/config/entity_dictionary/brands_base.csv`
   - `backend/config/semantic_sets/archive/brands_*.yml`
   - `backend/config/brand_noise.yaml`
   - `backend/config/nlp/stopwords/hard_neg_brands.txt`
   -> Verify the catalog reports source counts, duplicates, and rejected/noise overlaps.

2. Assign lifecycle by source:
   - `approved` from unified lexicon
   - `seed` from base CSV
   - `candidate` from archive brand packs
   - `rejected` from noise files
   -> Verify archive-only brands cannot become verified without Hotpost/Reddit evidence.

3. Re-run the dry-run digest from the catalog instead of only `unified_lexicon.yml`.
   -> Verify known base brands like Shopify, Etsy, PayPal, Stripe, Google, and Meta can be detected when evidence exists.

4. Add source-catalog tests.
   -> Verify lifecycle priority: rejected > approved > seed > candidate, and no Python hardcoded brand list.

## Phase R15.1: Quality Review Contract

Step -> validation point:

1. Add acceptance categories: `candidate`, `verified`, `rejected`.
   -> Verify unknown brands cannot become `verified` without evidence threshold.

2. Add review summary by interest tag.
   -> Verify brands map back to user-facing tags like AI tools, SEO/GEO, seller operations, product selection, or platform policy.

3. Add noise audit section.
   -> Verify generic words, people names, and community names are not silently accepted as brands.

## Phase R15.1.5: User-vetted Archive Pool Preaudit

Step -> validation point:

1. Treat `backend/config/semantic_sets/archive/brands_*.yml` as user-vetted historical brand resources, not weak auto-discovered candidates.
   -> Verify archive brands are cleaned and grouped for user audit before DB write.

2. Clean by trimming, normalizing, deduplicating, and merging domain memberships.
   -> Verify duplicate rows are counted and no source brand is silently deleted.

3. Classify by archive domain and configured display label.
   -> Verify review output includes per-domain counts and a full CSV/JSON/Markdown audit pack.

4. Flag noise overlaps for review, but do not reject user-vetted archive brands automatically.
   -> Verify `needs_review` is a review flag, not a deletion action.

## Phase R15.2: Dev DB Registry

Step -> validation point:

1. Add migration for `brand_registry` and `brand_mentions`.
   -> Verify migration applies to test/dev and has rollback.

2. Add idempotent Dev writer.
   -> Verify rerun does not duplicate brands or mentions.

3. Gate writes behind explicit command flag.
   -> Verify default remains dry-run.

4. Add DB tests.
   -> Verify insert, duplicate handling, status update, and rollback path.

## Phase R15.3: Daily Ops Sidecar

Step -> validation point:

1. Run brand digest after Hotpost release and mini snapshot.
   -> Verify it never blocks publish, snapshot, or cloud DB sync.

2. Add SOP section to daily ops.
   -> Verify daily operator reports: new brands, verified brands, rejected/noise, and DB write status.

3. Feed accepted brands back to semantic review queue.
   -> Verify semantic lexicon updates remain reviewed, not automatic.

## Phase R15.4: Consumer Surfaces

Step -> validation point:

1. Add read-only service for brand registry.
   -> Verify API/frontend/miniapp share the same backend source.

2. Add miniapp snapshot fields only after product review.
   -> Verify old miniapp card display remains stable.

## Completion Criteria

- R15.0 is complete when dry-run reports are generated from real published Hotpost cards with tests passing.
- R15.2 is complete only after Dev DB write is explicit, idempotent, tested, and rollbackable.
- Miniapp consumption starts only after registry quality is accepted.
