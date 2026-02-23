-- 优化 SCD2 触发器逻辑
-- 目标：避免仅 score/comments 变化时创建新版本
-- 运行环境：生产库 (reddit_signal_scanner)

BEGIN;

CREATE OR REPLACE FUNCTION public.trg_posts_raw_enforce_scd2()
RETURNS trigger
LANGUAGE plpgsql
AS $function$
BEGIN
    -- 场景 1: 新插入 (INSERT)
    -- 直接作为当前版本插入，版本号默认为 1
    IF (TG_OP = 'INSERT') THEN
        NEW.version := 1;
        NEW.is_current := true;
        NEW.valid_from := NOW();
        NEW.valid_to := '9999-12-31 00:00:00'::timestamp;
        RETURN NEW;
    END IF;

    -- 场景 2: 更新 (UPDATE)
    IF (TG_OP = 'UPDATE') THEN
        -- 检查是否为"实质性变更" (Title 或 Body 变化)
        -- 使用 IS DISTINCT FROM 处理 NULL 值
        IF (NEW.title IS DISTINCT FROM OLD.title OR NEW.body IS DISTINCT FROM OLD.body) THEN
            -- A. 实质变更 -> 执行标准的 SCD2 逻辑 (关旧开新)
            
            -- 1. 关闭旧版本
            UPDATE public.posts_raw
            SET is_current = false,
                valid_to = NOW()
            WHERE id = OLD.id;
            
            -- 2. 创建新版本 (作为新行插入)
            -- 注意：这里我们返回 NULL 以取消原始的 UPDATE 操作，
            -- 改为手动执行 INSERT。这是行级触发器的常见模式。
            INSERT INTO public.posts_raw (
                source, source_post_id, version, 
                created_at, fetched_at, valid_from, valid_to, is_current,
                author_id, author_name, title, body, body_norm, text_norm_hash,
                url, subreddit, score, num_comments, is_deleted, edit_count, lang, metadata
            ) VALUES (
                NEW.source, NEW.source_post_id, OLD.version + 1,
                OLD.created_at, NOW(), NOW(), '9999-12-31 00:00:00', true,
                NEW.author_id, NEW.author_name, NEW.title, NEW.body, NEW.body_norm, NEW.text_norm_hash,
                NEW.url, NEW.subreddit, NEW.score, NEW.num_comments, NEW.is_deleted, NEW.edit_count, NEW.lang, NEW.metadata
            );
            
            RETURN NULL; -- 取消原始 UPDATE，因为我们已经处理了插入
            
        ELSE
            -- B. 非实质变更 (仅分数、评论数、元数据变化) -> 原地更新 (In-Place Update)
            -- 保持版本号不变，仅更新统计字段
            NEW.version := OLD.version;
            NEW.valid_from := OLD.valid_from;
            NEW.valid_to := OLD.valid_to;
            NEW.is_current := OLD.is_current;
            
            -- 允许更新的字段: score, num_comments, fetched_at, metadata, etc.
            RETURN NEW;
        END IF;
    END IF;
    
    RETURN NULL;
END;
$function$;

COMMIT;
