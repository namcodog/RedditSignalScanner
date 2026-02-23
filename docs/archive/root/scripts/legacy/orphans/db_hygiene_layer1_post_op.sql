-- Layer 1.5: The Post-Op Care (Sync Only)
-- Wrapped in DO block for safety

DO $$
DECLARE
    count_hot_sync INTEGER;
    count_orphan_comments INTEGER;
    count_orphan_embeddings INTEGER;
    count_orphan_labels INTEGER;
BEGIN
    RAISE NOTICE 'Starting Layer 1.5 Post-Op Care...';

    -- 1. 同步热库
    DELETE FROM posts_hot
    WHERE source_post_id NOT IN (SELECT source_post_id FROM posts_raw);
    GET DIAGNOSTICS count_hot_sync = ROW_COUNT;
    RAISE NOTICE '✅ Synced posts_hot: Removed % orphaned cache entries.', count_hot_sync;

    -- 2.1 孤儿评论
    DELETE FROM comments
    WHERE post_id NOT IN (SELECT id FROM posts_raw);
    GET DIAGNOSTICS count_orphan_comments = ROW_COUNT;
    RAISE NOTICE '✅ Cleaned % orphan comments.', count_orphan_comments;

    -- 2.2 孤儿向量
    DELETE FROM post_embeddings
    WHERE post_id NOT IN (SELECT id FROM posts_raw);
    GET DIAGNOSTICS count_orphan_embeddings = ROW_COUNT;
    RAISE NOTICE '✅ Cleaned % orphan embeddings.', count_orphan_embeddings;

    -- 2.3 孤儿标签
    DELETE FROM post_semantic_labels
    WHERE post_id NOT IN (SELECT id FROM posts_raw);
    GET DIAGNOSTICS count_orphan_labels = ROW_COUNT;
    RAISE NOTICE '✅ Cleaned % orphan semantic labels.', count_orphan_labels;

END $$;