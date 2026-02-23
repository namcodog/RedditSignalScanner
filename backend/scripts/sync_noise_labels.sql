-- Sync Noise Labels to Main Table (Final Clean Version)
-- Wrapped in DO block to handle notices properly

DO $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE posts_raw
    SET value_score = 0,
        business_pool = 'noise',
        spam_category = 'external_noise_label'
    WHERE id IN (
        SELECT content_id 
        FROM noise_labels 
        WHERE content_type = 'post'
    )
    AND (business_pool != 'noise' OR business_pool IS NULL);
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RAISE NOTICE 'Synced % noise labels to posts_raw.', updated_count;
END $$;
