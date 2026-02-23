-- =================================================================
-- Reddit Signal Scanner - Phase C: Atom Layer Backfill (Fix)
-- Created by: David (Reddit Data Architect)
-- Date: 2025-12-11
-- Purpose: Flatten JSON tags from comment_scores into content_labels/entities
-- =================================================================

BEGIN;

-- 1. Flatten Pain Tags -> content_labels (Category='pain', Aspect=Tag Value)
INSERT INTO public.content_labels (content_type, content_id, category, aspect, confidence, source_model)
SELECT DISTINCT
    'comment',
    comment_id,
    'pain_tag',
    jsonb_array_elements_text(tags_analysis->'pain_tags'),
    90,
    'gemini-2.5-flash-lite'
FROM public.comment_scores
WHERE tags_analysis->'pain_tags' IS NOT NULL;

-- 2. Flatten Aspect Tags -> content_labels (Category='aspect', Aspect=Tag Value)
INSERT INTO public.content_labels (content_type, content_id, category, aspect, confidence, source_model)
SELECT DISTINCT
    'comment',
    comment_id,
    'aspect_tag',
    jsonb_array_elements_text(tags_analysis->'aspect_tags'),
    90,
    'gemini-2.5-flash-lite'
FROM public.comment_scores
WHERE tags_analysis->'aspect_tags' IS NOT NULL;

-- 3. Flatten Entities (Known) -> content_entities
INSERT INTO public.content_entities (content_type, content_id, entity, entity_type, source_model)
SELECT DISTINCT
    'comment',
    comment_id,
    jsonb_array_elements_text(entities_extracted->'known'),
    'known',
    'gemini-2.5-flash-lite'
FROM public.comment_scores
WHERE entities_extracted->'known' IS NOT NULL;

-- 4. Flatten Entities (New) -> content_entities
INSERT INTO public.content_entities (content_type, content_id, entity, entity_type, source_model)
SELECT DISTINCT
    'comment',
    comment_id,
    jsonb_array_elements_text(entities_extracted->'new'),
    'new',
    'gemini-2.5-flash-lite'
FROM public.comment_scores
WHERE entities_extracted->'new' IS NOT NULL;

COMMIT;