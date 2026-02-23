-- 修复 posts_raw SCD2 触发器：保留传入的 version，不再强制改为 1

-- 1) 重新创建函数，尊重传入 version，缺省时才降级为 1
CREATE OR REPLACE FUNCTION public.trg_posts_raw_enforce_scd2() RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    -- 场景 1: 新插入 (INSERT)
    -- 保留调用方提供的版本号；若为空则默认 1
    IF (TG_OP = 'INSERT') THEN
        NEW.version := COALESCE(NEW.version, 1);
        NEW.is_current := COALESCE(NEW.is_current, true);
        NEW.valid_from := COALESCE(NEW.valid_from, NOW());
        NEW.valid_to := COALESCE(NEW.valid_to, '9999-12-31 00:00:00'::timestamp);
        RETURN NEW;
    END IF;

    -- 场景 2: 更新 (UPDATE)
    IF (TG_OP = 'UPDATE') THEN
        -- 实质性变更：关旧开新
        IF (NEW.title IS DISTINCT FROM OLD.title OR NEW.body IS DISTINCT FROM OLD.body) THEN
            UPDATE public.posts_raw
            SET is_current = false,
                valid_to = NOW()
            WHERE id = OLD.id;

            INSERT INTO public.posts_raw (
                source, source_post_id, version,
                created_at, fetched_at, valid_from, valid_to, is_current,
                author_id, author_name, title, body, body_norm, text_norm_hash,
                url, subreddit, score, num_comments, is_deleted, edit_count, lang, metadata
            ) VALUES (
                NEW.source, NEW.source_post_id, COALESCE(NEW.version, OLD.version + 1),
                OLD.created_at, NOW(), NOW(), '9999-12-31 00:00:00', true,
                NEW.author_id, NEW.author_name, NEW.title, NEW.body, NEW.body_norm, NEW.text_norm_hash,
                NEW.url, NEW.subreddit, NEW.score, NEW.num_comments, NEW.is_deleted, NEW.edit_count, NEW.lang, NEW.metadata
            );
            RETURN NULL; -- 取消原始 UPDATE
        ELSE
            -- 非实质变更：原地更新
            NEW.version := OLD.version;
            NEW.valid_from := OLD.valid_from;
            NEW.valid_to := OLD.valid_to;
            NEW.is_current := OLD.is_current;
            RETURN NEW;
        END IF;
    END IF;

    RETURN NULL;
END;
$$;

-- 2) 重新创建触发器（如已存在则替换）
DROP TRIGGER IF EXISTS enforce_scd2_posts_raw ON public.posts_raw;
CREATE TRIGGER enforce_scd2_posts_raw
BEFORE INSERT OR UPDATE ON public.posts_raw
FOR EACH ROW EXECUTE FUNCTION public.trg_posts_raw_enforce_scd2();
