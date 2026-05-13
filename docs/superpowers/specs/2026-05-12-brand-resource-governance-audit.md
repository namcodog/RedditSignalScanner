# Brand Resource Governance Audit

Date: 2026-05-12

Status: DONE_WITH_CONCERNS

## Skill Route

- CEO review: SCOPE REDUCTION.
- Eng review: HOLD SCOPE.

Reason: the goal is not to invent another brand system. The goal is to turn existing scattered resources into one governed source chain that plugs into R15.

## Finding

The brand resources are real, but they are split across four roles:

| Source | Count | Current Role | Problem |
|---|---:|---|---|
| `backend/config/semantic_sets/unified_lexicon.yml` | 8 | approved semantic matching | R15.0 reads only this, so coverage is tiny. |
| `backend/config/entity_dictionary/brands_base.csv` | 31 | base cross-border seeds | Useful seed list, but not wired into R15. |
| `backend/config/semantic_sets/archive/brands_*.yml` | ~1693 | domain brand inventory | Too large/noisy to auto-approve; currently disconnected. |
| `backend/config/brand_noise.yaml` + `hard_neg_brands.txt` | 100+ | false-positive filtering | Useful guardrail, but not yet in R15 matching. |

## Root Cause

R15.0 uses `UnifiedLexicon(DEFAULT_LEXICON_PATH)` where the default is `unified_lexicon.yml`. That file is small and approved-only, so the report only finds brands already in that file.

The larger brand assets were never made part of one lifecycle model. They exist as lists, not as governed brand sources.

## Correct Model

Use one brand source compiler before DB write:

```text
approved semantic brands
        +
base seed brands
        +
archive domain brand packs
        +
noise filters
        |
        v
brand_source_catalog.json
        |
        v
R15 brand digest
        |
        v
brand_registry / brand_mentions later
```

## Lifecycle Contract

| Lifecycle | Meaning | Source |
|---|---|---|
| approved | Safe for direct known-brand matching | `unified_lexicon.yml` |
| seed | Important base brands, can produce candidates | `brands_base.csv` |
| candidate | Large domain inventory, must be evidence-verified | `archive/brands_*.yml` |
| rejected | Known false positives | `brand_noise.yaml`, `hard_neg_brands.txt` |

No archive brand should become `verified` just because it appears in a list. It needs Reddit evidence.

## Recommended R15 Insert

Add a new phase before R15.1:

### R15.0.5 Brand Source Catalog

Step -> validation point:

1. Build a read-only brand source loader.
   -> It loads approved, seed, candidate, and rejected sources into one normalized catalog.

2. Generate an audit report.
   -> It reports source counts, duplicates, conflicts, and noise overlaps.

3. Re-run brand digest from the unified catalog.
   -> It should find Shopify/Etsy/PayPal/Stripe/Google/Meta when evidence exists, but keep archive-only hits as `candidate`.

4. Add tests.
   -> It proves lifecycle priority: rejected beats candidate; approved beats seed; aliases normalize.

## Do Not Do

- Do not paste 1693 archive brands into `unified_lexicon.yml`.
- Do not write DB before source catalog audit passes.
- Do not let miniapp own brand lists.
- Do not treat CSV/archive membership as verification.
- Do not hardcode product/domain brand lists in Python.

## Accepted Architecture

```text
brand_source_catalog
  source governance: approved / seed / candidate / rejected

brand_digest
  evidence extraction from Hotpost cards using the source catalog

brand_registry
  DB asset table, only after source catalog and quality contract pass

semantic lexicon
  approved matching/aliases only, not the whole brand warehouse
```

## Product Impact

This makes the scattered lists useful without polluting the system. We keep the wide historical inventory as a discovery net, while the DB only receives brands with evidence and reviewed status.

Final recommendation: insert R15.0.5 now, then proceed to R15.1 quality status and R15.2 Dev DB.
