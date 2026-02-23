-- Layer 1: The Surgeon's Scalpel (V3 - Dependency Handled)
-- 包含对 post_semantic_labels 和 posts_raw 自引用的处理

DO $$
DECLARE
    count_archived INTEGER := 0;
    count_deleted_ghosts INTEGER := 0;
    count_deleted_shorts INTEGER := 0;
    count_deleted_dups INTEGER := 0;
    remaining_total INTEGER;
    
    -- 定义临时表来存要删除的ID，避免重复扫描
    target_ids BIGINT[];
BEGIN
    RAISE NOTICE 'Starting Layer 1 Cleanup (V3)...';

    -- 创建临时表存要删的ID
    CREATE TEMP TABLE IF NOT EXISTS temp_deletion_targets (
        id BIGINT PRIMARY KEY,
        reason TEXT
    );
    -- 清空（以防万一）
    TRUNCATE temp_deletion_targets;

    -- ==========================================
    -- 1. 标记：老古董 (Ancients)
    -- ==========================================
    INSERT INTO temp_deletion_targets (id, reason)
    SELECT id, 'ancient'
    FROM posts_raw
    WHERE created_at < NOW() - INTERVAL '3 years';

    -- 归档操作 (Move to Archive)
    INSERT INTO posts_archive (source, source_post_id, version, payload, archived_at)
    SELECT 
        source, 
        source_post_id, 
        version, 
        to_jsonb(posts_raw) - 'id', 
        NOW()
    FROM posts_raw
    WHERE id IN (SELECT id FROM temp_deletion_targets WHERE reason = 'ancient');
    
    GET DIAGNOSTICS count_archived = ROW_COUNT;

    -- ==========================================
    -- 2. 标记：幽灵 (Ghosts)
    -- ==========================================
    INSERT INTO temp_deletion_targets (id, reason)
    SELECT id, 'ghost'
    FROM posts_raw 
    WHERE ((title IS NULL OR trim(title) = '') 
       OR (body IS NOT NULL AND trim(body) IN ('[deleted]', '[removed]'))
       OR (is_deleted = true))
    ON CONFLICT (id) DO NOTHING; -- 避免和ancient重叠

    -- ==========================================
    -- 3. 标记：短内容 (Shorts)
    -- ==========================================
    INSERT INTO temp_deletion_targets (id, reason)
    SELECT id, 'short'
    FROM posts_raw 
    WHERE length(coalesce(title, '') || ' ' || coalesce(body, '')) < 10
    ON CONFLICT (id) DO NOTHING;

    -- ==========================================
    -- 4. 标记：重复 (Duplicates)
    -- ==========================================
    INSERT INTO temp_deletion_targets (id, reason)
    SELECT id, 'duplicate'
    FROM (
        SELECT 
            id,
            ROW_NUMBER() OVER (
                PARTITION BY text_norm_hash 
                ORDER BY fetched_at DESC, version DESC, id DESC
            ) as rn
        FROM posts_raw
        WHERE text_norm_hash IS NOT NULL
    ) duplicates
    WHERE rn > 1
    ON CONFLICT (id) DO NOTHING;

    -- ==========================================
    -- 5. 执行清理 (Execution)
    -- ==========================================
    
    -- 5.1 先清理 post_semantic_labels (RESTRICT 约束)
    DELETE FROM post_semantic_labels
    WHERE post_id IN (SELECT id FROM temp_deletion_targets);
    
    RAISE NOTICE 'Cleaned dependent table: post_semantic_labels';

    -- 5.2 处理 posts_raw 自引用 (duplicate_of_id)
    -- 如果要删的帖子被别人引用了，把别人的 duplicate_of_id 置空
    UPDATE posts_raw
    SET duplicate_of_id = NULL
    WHERE duplicate_of_id IN (SELECT id FROM temp_deletion_targets);

    RAISE NOTICE 'Cleaned dependent references: posts_raw.duplicate_of_id';

    -- 5.3 终于可以删主表了 (Cascade 会自动处理 comments 和 embeddings)
    DELETE FROM posts_raw
    WHERE id IN (SELECT id FROM temp_deletion_targets);

    -- 统计各类删除数量
    SELECT COUNT(*) INTO count_deleted_ghosts FROM temp_deletion_targets WHERE reason = 'ghost';
    SELECT COUNT(*) INTO count_deleted_shorts FROM temp_deletion_targets WHERE reason = 'short';
    SELECT COUNT(*) INTO count_deleted_dups FROM temp_deletion_targets WHERE reason = 'duplicate';

    -- ==========================================
    -- 6. 最终统计
    -- ==========================================
    SELECT COUNT(*) INTO remaining_total FROM posts_raw;
    
    RAISE NOTICE '---------------------------------------------------';
    RAISE NOTICE '✅ Archived Ancients: %', count_archived;
    RAISE NOTICE '✅ Deleted Ghosts: %', count_deleted_ghosts;
    RAISE NOTICE '✅ Deleted Shorts: %', count_deleted_shorts;
    RAISE NOTICE '✅ Deleted Duplicates: %', count_deleted_dups;
    RAISE NOTICE '🎉 Total Cleaned: %', (SELECT COUNT(*) FROM temp_deletion_targets);
    RAISE NOTICE '📊 Current posts_raw Size: %', remaining_total;
    RAISE NOTICE '---------------------------------------------------';

END $$;
