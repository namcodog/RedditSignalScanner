# Brand Intelligence CEO Review

Date: 2026-05-12

## Scope Mode

SCOPE REDUCTION.

Reason: brand intelligence is valuable, but the first useful version is not a new product surface. The first version should prove that the main system can collect brands with evidence from published Hotpost cards and existing semantic/entity data.

## Step 0 Challenge

1. Is this the right problem?
   Yes. Community recommendation answers "where to look"; brand intelligence answers "what brands/tools/products are being discussed". This is a real extension of the current product direction.

2. Is there a simpler path?
   Yes. Do not start with miniapp UI, full API, or production DB writes. Start with a dry-run brand report from existing published cards.

3. What if we do nothing?
   We can still recommend communities, but we miss a higher-value asset: which brands are rising, being compared, complained about, or used as truth-source examples inside those communities.

## Existing Leverage

- Hotpost already produces reviewed, evidence-backed cards.
- `content_entities` already records content-level entities, including brands.
- Semantic lexicon already has brand terms and aliases.
- Community recommendation already reads semantic/entity evidence.

This means we should extend the existing data chain, not build a separate crawler or a miniapp-owned brand list.

## 12 Month State

```text
Current:
  communities + cards + semantic terms

R15 delta:
  brand registry + brand evidence + daily brand digest

12 month target:
  every domain tag can show active communities, discussed brands, evidence posts,
  and rising/declining brand signals without manual maintenance.
```

## Scope Decision

| Proposal | Decision | Reason |
|---|---|---|
| New `brand_registry` as brand asset table | Accept | Brand is a business asset, not a community and not only a semantic term. |
| Reuse `content_entities` as the brand master table | Reject | It records mentions, not the canonical brand asset. |
| Store brands only in semantic lexicon | Reject | Semantic lexicon is matching/normalization, not evidence or lifecycle state. |
| Miniapp displays brands in first pass | Defer | Display before data quality would create noisy product surface. |
| Hotpost prompt writes brand fields directly | Reject | Too easy to hallucinate. Extract from evidence after publishing first. |
| Use published Hotpost cards as first source | Accept | They are already reviewed and evidence-backed. |
| Add DB writes immediately | Defer to R15.2 | First dry-run should prove extraction quality. |

## Accepted Scope

- Build a backend brand intelligence chain owned by the main system.
- First source is published Hotpost cards and their evidence text.
- Use semantic lexicon and existing `content_entities` as supporting evidence.
- Produce reports before DB writes.
- Dev DB write comes only after dry-run quality is accepted.
- Miniapp and other branches consume the output later.

## Deferred

- User-facing miniapp brand page.
- Public API.
- Gold DB writes.
- Automated promotion from candidate brand to verified brand.
- Brand trend scoring beyond basic counts and recency.
