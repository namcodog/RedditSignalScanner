-- Roll back only rows inserted by community_pool Phase 2 Dev write.
BEGIN;
DELETE FROM community_category_map
WHERE community_id IN (
  SELECT id FROM community_pool
  WHERE name IN ('r/ppc', 'r/claudecode', 'r/giftideas', 'r/kickstarter', 'r/productmanagement', 'r/ai_agents', 'r/llm', 'r/analytics', 'r/google_ads', 'r/googleads', 'r/adops', 'r/campinggear', 'r/projectmanagement', 'r/asianbeauty', 'r/content_marketing', 'r/cursor', 'r/juststart', 'r/productivity', 'r/entrepreneurridealong', 'r/experienceddevs', 'r/machinelearning', 'r/stationery', 'r/b2bmarketing', 'r/codex', 'r/managers', 'r/sales', 'r/skincareaddiction', 'r/agi', 'r/beagles', 'r/chatgptcoding', 'r/claudeskills', 'r/contentcreators', 'r/customersupport', 'r/emailmarketing', 'r/helpdesk', 'r/hobonichi', 'r/openwebui', 'r/perplexity_ai', 'r/pkms', 'r/programming', 'r/research', 'r/revops', 'r/seogrowth', 'r/substack', 'r/sysadmin', 'r/writing', 'r/apartmenthacks', 'r/askmarketing', 'r/blogging', 'r/comfyui', 'r/consulting', 'r/fountainpens', 'r/journaling', 'r/opensourceai', 'r/planners', 'r/sidehustle')
    AND description_keywords->>'source' = 'community_pool_phase2_dev_write'
);
DELETE FROM community_pool
WHERE name IN ('r/ppc', 'r/claudecode', 'r/giftideas', 'r/kickstarter', 'r/productmanagement', 'r/ai_agents', 'r/llm', 'r/analytics', 'r/google_ads', 'r/googleads', 'r/adops', 'r/campinggear', 'r/projectmanagement', 'r/asianbeauty', 'r/content_marketing', 'r/cursor', 'r/juststart', 'r/productivity', 'r/entrepreneurridealong', 'r/experienceddevs', 'r/machinelearning', 'r/stationery', 'r/b2bmarketing', 'r/codex', 'r/managers', 'r/sales', 'r/skincareaddiction', 'r/agi', 'r/beagles', 'r/chatgptcoding', 'r/claudeskills', 'r/contentcreators', 'r/customersupport', 'r/emailmarketing', 'r/helpdesk', 'r/hobonichi', 'r/openwebui', 'r/perplexity_ai', 'r/pkms', 'r/programming', 'r/research', 'r/revops', 'r/seogrowth', 'r/substack', 'r/sysadmin', 'r/writing', 'r/apartmenthacks', 'r/askmarketing', 'r/blogging', 'r/comfyui', 'r/consulting', 'r/fountainpens', 'r/journaling', 'r/opensourceai', 'r/planners', 'r/sidehustle')
  AND description_keywords->>'source' = 'community_pool_phase2_dev_write';
COMMIT;
