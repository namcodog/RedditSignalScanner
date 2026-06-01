-- Roll back only rows inserted by Hotpost community-pool R12 Dev write.
BEGIN;
DELETE FROM community_category_map
WHERE community_id IN (
  SELECT id FROM community_pool
  WHERE name IN ('r/ebayselleradvice')
    AND description_keywords->>'source' = 'hotpost_community_pool_r12_dev_write'
);
DELETE FROM community_pool
WHERE name IN ('r/ebayselleradvice')
  AND description_keywords->>'source' = 'hotpost_community_pool_r12_dev_write';
COMMIT;
