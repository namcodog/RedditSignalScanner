--
-- PostgreSQL database dump
--

\restrict dXdJDXVBp97S7IgFNrOubwihxJKMgzm7s9lMnR4sYoBcHkBcQnQW2VbyBaJJvOa

-- Dumped from database version 14.19 (Homebrew)
-- Dumped by pg_dump version 14.19 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: comments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.comments (
    id bigint NOT NULL,
    reddit_comment_id character varying(32) NOT NULL,
    source character varying(50) DEFAULT 'reddit'::character varying NOT NULL,
    source_post_id character varying(100) NOT NULL,
    subreddit character varying(100) NOT NULL,
    parent_id character varying(32),
    depth integer DEFAULT 0 NOT NULL,
    body text NOT NULL,
    author_id character varying(100),
    author_name character varying(100),
    author_created_utc timestamp with time zone,
    created_utc timestamp with time zone NOT NULL,
    score integer DEFAULT 0 NOT NULL,
    is_submitter boolean DEFAULT false NOT NULL,
    distinguished character varying(32),
    edited boolean DEFAULT false NOT NULL,
    permalink text,
    removed_by_category character varying(64),
    awards_count integer DEFAULT 0 NOT NULL,
    captured_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at timestamp with time zone,
    post_id bigint NOT NULL,
    CONSTRAINT ck_comments_ck_comments_depth_non_negative CHECK ((depth >= 0))
);


ALTER TABLE public.comments OWNER TO postgres;

--
-- Name: comments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.comments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.comments_id_seq OWNER TO postgres;

--
-- Name: comments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.comments_id_seq OWNED BY public.comments.id;


--
-- Name: community_cache; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.community_cache (
    community_name character varying(100) NOT NULL,
    last_crawled_at timestamp with time zone,
    ttl_seconds integer DEFAULT 3600 NOT NULL,
    posts_cached integer DEFAULT 0 NOT NULL,
    hit_count integer DEFAULT 0 NOT NULL,
    last_hit_at timestamp with time zone,
    crawl_priority integer DEFAULT 50 NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    crawl_frequency_hours integer DEFAULT 2 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    empty_hit integer DEFAULT 0 NOT NULL,
    success_hit integer DEFAULT 0 NOT NULL,
    failure_hit integer DEFAULT 0 NOT NULL,
    avg_valid_posts integer DEFAULT 0 NOT NULL,
    quality_tier character varying(20) NOT NULL,
    last_seen_post_id character varying(100),
    last_seen_created_at timestamp with time zone,
    total_posts_fetched integer DEFAULT 0 NOT NULL,
    dedup_rate numeric(5,2),
    member_count integer,
    crawl_quality_score numeric(3,2) DEFAULT 0.0 NOT NULL,
    CONSTRAINT ck_cache_avg_valid_nonneg CHECK ((avg_valid_posts >= 0)),
    CONSTRAINT ck_cache_empty_hit_nonneg CHECK ((empty_hit >= 0)),
    CONSTRAINT ck_cache_failure_hit_nonneg CHECK ((failure_hit >= 0)),
    CONSTRAINT ck_cache_quality_range CHECK (((crawl_quality_score >= (0)::numeric) AND (crawl_quality_score <= (10)::numeric))),
    CONSTRAINT ck_cache_success_hit_nonneg CHECK ((success_hit >= 0)),
    CONSTRAINT ck_cache_total_nonneg CHECK ((total_posts_fetched >= 0)),
    CONSTRAINT ck_community_cache_ck_community_cache_member_count_non_negative CHECK (((member_count IS NULL) OR (member_count >= 0))),
    CONSTRAINT ck_community_cache_ck_community_cache_name_format CHECK (((community_name)::text ~ '^r/[a-zA-Z0-9_]+$'::text)),
    CONSTRAINT ck_community_cache_hit_count_non_negative CHECK ((hit_count >= 0)),
    CONSTRAINT ck_community_cache_name_format CHECK (((community_name)::text ~ '^r/[a-zA-Z0-9_]+$'::text)),
    CONSTRAINT ck_community_cache_posts_non_negative CHECK ((posts_cached >= 0)),
    CONSTRAINT ck_community_cache_priority_range CHECK (((crawl_priority >= 1) AND (crawl_priority <= 100))),
    CONSTRAINT ck_community_cache_ttl_positive CHECK ((ttl_seconds > 0))
);


ALTER TABLE public.community_cache OWNER TO postgres;

--
-- Name: TABLE community_cache; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.community_cache IS '社区缓存元数据表 - Reddit社区数据的缓存状态管理，支持LRU + TTL + Priority三重缓存策略';


--
-- Name: COLUMN community_cache.community_name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.community_name IS 'Reddit社区名称，如r/startups';


--
-- Name: COLUMN community_cache.last_crawled_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.last_crawled_at IS '最后抓取时间，NULL表示从未抓取';


--
-- Name: COLUMN community_cache.ttl_seconds; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.ttl_seconds IS '缓存生存时间（秒）';


--
-- Name: COLUMN community_cache.posts_cached; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.posts_cached IS '当前缓存的帖子数量';


--
-- Name: COLUMN community_cache.hit_count; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.hit_count IS '缓存命中次数';


--
-- Name: COLUMN community_cache.last_hit_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.last_hit_at IS '最后访问时间';


--
-- Name: COLUMN community_cache.crawl_priority; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.crawl_priority IS '爬虫优先级(1-100)，1为最高';


--
-- Name: COLUMN community_cache.created_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.created_at IS '缓存条目创建时间';


--
-- Name: COLUMN community_cache.updated_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.updated_at IS '缓存元数据最后更新时间';


--
-- Name: COLUMN community_cache.last_seen_post_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.last_seen_post_id IS '水位线：最后抓取的帖子ID';


--
-- Name: COLUMN community_cache.last_seen_created_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.last_seen_created_at IS '水位线：最后抓取的帖子创建时间';


--
-- Name: COLUMN community_cache.total_posts_fetched; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.total_posts_fetched IS '累计抓取的帖子数';


--
-- Name: COLUMN community_cache.dedup_rate; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.dedup_rate IS '去重率（%）';


--
-- Name: COLUMN community_cache.member_count; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.community_cache.member_count IS 'Number of members in the community (from Reddit API)';


--
-- Name: community_pool; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.community_pool (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    tier character varying(20) NOT NULL,
    categories jsonb NOT NULL,
    description_keywords jsonb NOT NULL,
    daily_posts integer DEFAULT 0 NOT NULL,
    avg_comment_length integer DEFAULT 0 NOT NULL,
    user_feedback_count integer DEFAULT 0 NOT NULL,
    discovered_count integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    priority character varying(20) DEFAULT 'medium'::character varying NOT NULL,
    is_blacklisted boolean DEFAULT false NOT NULL,
    blacklist_reason character varying(255),
    downrank_factor numeric(3,2),
    created_by uuid,
    updated_by uuid,
    deleted_at timestamp with time zone,
    deleted_by uuid,
    semantic_quality_score numeric(3,2) NOT NULL,
    health_status character varying(20) DEFAULT 'unknown'::character varying NOT NULL,
    last_evaluated_at timestamp with time zone,
    auto_tier_enabled boolean DEFAULT false NOT NULL,
    CONSTRAINT ck_community_pool_ck_community_pool_name_format CHECK (((name)::text ~ '^r/[a-zA-Z0-9_]+$'::text)),
    CONSTRAINT ck_community_pool_ck_community_pool_name_len CHECK (((char_length((name)::text) >= 3) AND (char_length((name)::text) <= 100))),
    CONSTRAINT ck_community_pool_name_format CHECK (((name)::text ~ '^r/[a-zA-Z0-9_]+$'::text))
);


ALTER TABLE public.community_pool OWNER TO postgres;

--
-- Name: community_pool_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.community_pool_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.community_pool_id_seq OWNER TO postgres;

--
-- Name: community_pool_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.community_pool_id_seq OWNED BY public.community_pool.id;


--
-- Name: posts_hot; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.posts_hot (
    source character varying(50) DEFAULT 'reddit'::character varying NOT NULL,
    source_post_id character varying(100) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    cached_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone DEFAULT (now() + '180 days'::interval) NOT NULL,
    title text NOT NULL,
    body text,
    subreddit character varying(100) NOT NULL,
    score integer DEFAULT 0,
    num_comments integer DEFAULT 0,
    metadata jsonb,
    id bigint DEFAULT nextval('public.posts_hot_id_seq'::regclass) NOT NULL,
    author_id character varying(100),
    author_name character varying(100),
    content_labels jsonb,
    entities jsonb
);


ALTER TABLE public.posts_hot OWNER TO postgres;

--
-- Name: TABLE posts_hot; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.posts_hot IS '热缓存：覆盖式刷新，保留24-72小时，用于实时分析';


--
-- Name: posts_raw; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.posts_raw (
    id bigint NOT NULL,
    source character varying(50) DEFAULT 'reddit'::character varying NOT NULL,
    source_post_id character varying(100) NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone NOT NULL,
    fetched_at timestamp with time zone DEFAULT now() NOT NULL,
    valid_from timestamp with time zone DEFAULT now() NOT NULL,
    valid_to timestamp with time zone DEFAULT '9999-12-31 08:00:00+08'::timestamp with time zone,
    is_current boolean DEFAULT true NOT NULL,
    author_id character varying(100),
    author_name character varying(100),
    title text NOT NULL,
    body text,
    body_norm text,
    text_norm_hash character varying(64),
    url text,
    subreddit character varying(100) NOT NULL,
    score integer DEFAULT 0,
    num_comments integer DEFAULT 0,
    is_deleted boolean DEFAULT false,
    edit_count integer DEFAULT 0,
    lang character varying(10),
    metadata jsonb,
    CONSTRAINT ck_posts_raw_valid_period CHECK (((valid_from < valid_to) OR (valid_to = '9999-12-31 00:00:00'::timestamp without time zone))),
    CONSTRAINT ck_posts_raw_version_positive CHECK ((version > 0))
);


ALTER TABLE public.posts_raw OWNER TO postgres;

--
-- Name: TABLE posts_raw; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.posts_raw IS '冷库：增量累积，保留90天滚动窗口，用于算法训练、趋势分析、回测';


--
-- Name: COLUMN posts_raw.version; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.posts_raw.version IS 'SCD2: 版本号，每次编辑+1';


--
-- Name: COLUMN posts_raw.is_current; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.posts_raw.is_current IS 'SCD2: 是否当前版本';


--
-- Name: COLUMN posts_raw.text_norm_hash; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.posts_raw.text_norm_hash IS '文本归一化哈希，用于去重（防止转贴/改写）';


--
-- Name: posts_raw_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.posts_raw_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.posts_raw_id_seq OWNER TO postgres;

--
-- Name: posts_raw_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.posts_raw_id_seq OWNED BY public.posts_raw.id;


--
-- Name: comments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.comments ALTER COLUMN id SET DEFAULT nextval('public.comments_id_seq'::regclass);


--
-- Name: community_pool id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_pool ALTER COLUMN id SET DEFAULT nextval('public.community_pool_id_seq'::regclass);


--
-- Name: posts_raw id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posts_raw ALTER COLUMN id SET DEFAULT nextval('public.posts_raw_id_seq'::regclass);


--
-- Name: community_pool ck_pool_categories_jsonb; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE public.community_pool
    ADD CONSTRAINT ck_pool_categories_jsonb CHECK (((categories IS NULL) OR (jsonb_typeof(categories) = ANY (ARRAY['array'::text, 'object'::text])))) NOT VALID;


--
-- Name: community_pool ck_pool_keywords_jsonb; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE public.community_pool
    ADD CONSTRAINT ck_pool_keywords_jsonb CHECK (((description_keywords IS NULL) OR (jsonb_typeof(description_keywords) = ANY (ARRAY['array'::text, 'object'::text])))) NOT VALID;


--
-- Name: posts_hot ck_posts_hot_entities_jsonb; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE public.posts_hot
    ADD CONSTRAINT ck_posts_hot_entities_jsonb CHECK (((entities IS NULL) OR (jsonb_typeof(entities) = ANY (ARRAY['object'::text, 'array'::text])))) NOT VALID;


--
-- Name: posts_hot ck_posts_hot_labels_jsonb; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE public.posts_hot
    ADD CONSTRAINT ck_posts_hot_labels_jsonb CHECK (((content_labels IS NULL) OR (jsonb_typeof(content_labels) = ANY (ARRAY['object'::text, 'array'::text])))) NOT VALID;


--
-- Name: posts_hot ck_posts_hot_metadata_jsonb; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE public.posts_hot
    ADD CONSTRAINT ck_posts_hot_metadata_jsonb CHECK (((metadata IS NULL) OR (jsonb_typeof(metadata) = ANY (ARRAY['object'::text, 'array'::text])))) NOT VALID;


--
-- Name: posts_raw ck_posts_raw_metadata_jsonb; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE public.posts_raw
    ADD CONSTRAINT ck_posts_raw_metadata_jsonb CHECK (((metadata IS NULL) OR (jsonb_typeof(metadata) = ANY (ARRAY['object'::text, 'array'::text])))) NOT VALID;


--
-- Name: community_cache community_cache_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_cache
    ADD CONSTRAINT community_cache_pkey PRIMARY KEY (community_name);


--
-- Name: comments pk_comments; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT pk_comments PRIMARY KEY (id);


--
-- Name: community_pool pk_community_pool; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_pool
    ADD CONSTRAINT pk_community_pool PRIMARY KEY (id);


--
-- Name: posts_raw pk_posts_raw; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posts_raw
    ADD CONSTRAINT pk_posts_raw PRIMARY KEY (id);


--
-- Name: posts_hot posts_hot_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posts_hot
    ADD CONSTRAINT posts_hot_pkey PRIMARY KEY (id);


--
-- Name: comments uq_comments_reddit_comment_id; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT uq_comments_reddit_comment_id UNIQUE (reddit_comment_id);


--
-- Name: community_pool uq_community_pool_name; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_pool
    ADD CONSTRAINT uq_community_pool_name UNIQUE (name);


--
-- Name: posts_raw uq_posts_raw_source_version; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posts_raw
    ADD CONSTRAINT uq_posts_raw_source_version UNIQUE (source, source_post_id, version);


--
-- Name: idx_cache_quality_tier; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_cache_quality_tier ON public.community_cache USING btree (quality_tier);


--
-- Name: idx_cache_ttl_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_cache_ttl_active ON public.community_cache USING btree (is_active, last_crawled_at, ttl_seconds) WHERE (is_active = true);


--
-- Name: idx_comments_captured_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_comments_captured_at ON public.comments USING btree (captured_at);


--
-- Name: idx_comments_expires_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_comments_expires_at ON public.comments USING btree (expires_at);


--
-- Name: idx_comments_parent_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_comments_parent_id ON public.comments USING btree (parent_id);


--
-- Name: idx_comments_post_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_comments_post_id ON public.comments USING btree (post_id);


--
-- Name: idx_comments_post_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_comments_post_time ON public.comments USING btree (source, source_post_id, created_utc);


--
-- Name: idx_comments_subreddit_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_comments_subreddit_time ON public.comments USING btree (subreddit, created_utc);


--
-- Name: idx_community_cache_crawl_frequency; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_community_cache_crawl_frequency ON public.community_cache USING btree (crawl_frequency_hours);


--
-- Name: idx_community_cache_is_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_community_cache_is_active ON public.community_cache USING btree (is_active);


--
-- Name: idx_community_cache_member_count; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_community_cache_member_count ON public.community_cache USING btree (member_count);


--
-- Name: idx_community_cache_name_trgm; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_community_cache_name_trgm ON public.community_cache USING gin (community_name public.gin_trgm_ops);


--
-- Name: idx_community_cache_ttl; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_community_cache_ttl ON public.community_cache USING btree (last_crawled_at, ttl_seconds) WHERE ((last_crawled_at IS NOT NULL) AND (ttl_seconds IS NOT NULL) AND (ttl_seconds > 0));


--
-- Name: idx_community_pool_categories_gin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_community_pool_categories_gin ON public.community_pool USING gin (categories);


--
-- Name: idx_community_pool_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_community_pool_deleted_at ON public.community_pool USING btree (deleted_at);


--
-- Name: idx_community_pool_is_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_community_pool_is_active ON public.community_pool USING btree (is_active);


--
-- Name: idx_community_pool_tier; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_community_pool_tier ON public.community_pool USING btree (tier);


--
-- Name: idx_posts_hot_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_hot_created_at ON public.posts_hot USING btree (created_at DESC);


--
-- Name: idx_posts_hot_expires_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_hot_expires_at ON public.posts_hot USING btree (expires_at);


--
-- Name: idx_posts_hot_subreddit; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_hot_subreddit ON public.posts_hot USING btree (subreddit, created_at DESC);


--
-- Name: idx_posts_hot_subreddit_expires; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_hot_subreddit_expires ON public.posts_hot USING btree (subreddit, expires_at);


--
-- Name: idx_posts_raw_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_raw_created_at ON public.posts_raw USING btree (created_at DESC);


--
-- Name: idx_posts_raw_current; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_raw_current ON public.posts_raw USING btree (source, source_post_id, is_current) WHERE (is_current = true);


--
-- Name: idx_posts_raw_fetched_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_raw_fetched_at ON public.posts_raw USING btree (fetched_at DESC);


--
-- Name: idx_posts_raw_source_post_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_raw_source_post_id ON public.posts_raw USING btree (source, source_post_id);


--
-- Name: idx_posts_raw_subreddit; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_raw_subreddit ON public.posts_raw USING btree (subreddit, created_at DESC);


--
-- Name: idx_posts_raw_text_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_posts_raw_text_hash ON public.posts_raw USING btree (text_norm_hash);


--
-- Name: ix_community_cache_crawl_schedule; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_community_cache_crawl_schedule ON public.community_cache USING btree (crawl_priority, last_crawled_at) WHERE (last_crawled_at IS NULL);


--
-- Name: ix_community_cache_freshness; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_community_cache_freshness ON public.community_cache USING btree (last_crawled_at DESC) WHERE (last_crawled_at IS NOT NULL);


--
-- Name: ix_community_cache_hotness; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_community_cache_hotness ON public.community_cache USING btree (hit_count DESC, last_hit_at DESC);


--
-- Name: ix_community_cache_size; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_community_cache_size ON public.community_cache USING btree (posts_cached DESC) WHERE (posts_cached > 0);


--
-- Name: uq_posts_hot_source_post; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX uq_posts_hot_source_post ON public.posts_hot USING btree (source, source_post_id);


--
-- Name: posts_raw enforce_scd2_posts_raw; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER enforce_scd2_posts_raw BEFORE INSERT OR UPDATE ON public.posts_raw FOR EACH ROW EXECUTE FUNCTION public.trg_posts_raw_enforce_scd2();


--
-- Name: posts_raw trg_fill_normalized_fields; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_fill_normalized_fields BEFORE INSERT OR UPDATE ON public.posts_raw FOR EACH ROW EXECUTE FUNCTION public.fill_normalized_fields();


--
-- Name: comments trg_set_comment_expires; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_set_comment_expires BEFORE INSERT ON public.comments FOR EACH ROW EXECUTE FUNCTION public.set_comment_expires_at();


--
-- Name: community_cache update_community_cache_hit_stats; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_community_cache_hit_stats BEFORE UPDATE OF hit_count ON public.community_cache FOR EACH ROW EXECUTE FUNCTION public.update_cache_hit_stats();


--
-- Name: community_cache update_community_cache_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_community_cache_updated_at BEFORE UPDATE ON public.community_cache FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: comments fk_comments_posts_raw; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT fk_comments_posts_raw FOREIGN KEY (post_id) REFERENCES public.posts_raw(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;


--
-- Name: community_cache fk_community_cache_pool; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_cache
    ADD CONSTRAINT fk_community_cache_pool FOREIGN KEY (community_name) REFERENCES public.community_pool(name) ON DELETE CASCADE;


--
-- Name: community_pool fk_community_pool_created_by; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_pool
    ADD CONSTRAINT fk_community_pool_created_by FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: community_pool fk_community_pool_deleted_by; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_pool
    ADD CONSTRAINT fk_community_pool_deleted_by FOREIGN KEY (deleted_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: community_pool fk_community_pool_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_pool
    ADD CONSTRAINT fk_community_pool_updated_by FOREIGN KEY (updated_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

\unrestrict dXdJDXVBp97S7IgFNrOubwihxJKMgzm7s9lMnR4sYoBcHkBcQnQW2VbyBaJJvOa

