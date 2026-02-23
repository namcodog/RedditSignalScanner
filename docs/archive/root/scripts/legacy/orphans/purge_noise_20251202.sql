-- Purge Technical Noise & Irrelevant Communities
-- Date: 2025-12-02
-- Objective: Hard delete known technical/programming/IT communities and their data (posts, comments, vectors).

BEGIN;

-- 1. Define the Blacklist of Noise Communities
CREATE TEMP TABLE noise_communities (name VARCHAR(100));
INSERT INTO noise_communities (name) VALUES
('r/googlecloud'), ('r/sales'), ('r/saas'), ('r/dotnet'), ('r/aws'), ('r/golang'), 
('r/frontend'), ('r/csharp'), ('r/python'), ('r/rails'), ('r/docker'), ('r/java'), 
('r/node'), ('r/angular'), ('r/backend'), ('r/artificial'), ('r/kubernetes'), 
('r/webdesign'), ('r/productmanagement'), ('r/rust'), ('r/deeplearning'), ('r/devops'), 
('r/uxdesign'), ('r/machinelearning'), ('r/dataengineering'), ('r/django'), ('r/azure'), 
('r/javascript'), ('r/reactjs'), ('r/vuejs'), ('r/ui_design'), ('r/postgresql'), 
('r/datascience'), ('r/bigdata'), ('r/database'), ('r/typescript'), ('r/mongodb'), 
('r/consulting'), ('r/laravel'), ('r/venturecapital'),
-- Additional ones from analysis context if any
('r/cpp'), ('r/linux'), ('r/sysadmin'), ('r/programming'), ('r/technology');

-- 2. Delete Posts (Data Layer)
-- This is the heavy lifting. Comments and Embeddings will be deleted via CASCADE if FK exists.
-- If not, we delete them explicitly just to be safe.

-- 2.1 Delete Embeddings (Explicit safety, though CASCADE usually handles it)
DELETE FROM post_embeddings
WHERE post_id IN (
    SELECT id FROM posts_raw 
    WHERE subreddit IN (SELECT name FROM noise_communities)
);

-- 2.2 Delete Comments (Explicit safety)
DELETE FROM comments
WHERE subreddit IN (SELECT name FROM noise_communities);

-- 2.3 Delete Posts (The Source)
DELETE FROM posts_raw
WHERE subreddit IN (SELECT name FROM noise_communities);

-- 3. Delete Metadata (Structure Layer)

-- 3.1 Delete from Map
DELETE FROM community_category_map
WHERE community_id IN (
    SELECT id FROM community_pool 
    WHERE name IN (SELECT name FROM noise_communities)
);

-- 3.2 Delete from Pool
DELETE FROM community_pool
WHERE name IN (SELECT name FROM noise_communities);

-- 3.3 Delete from Cache
DELETE FROM community_cache
WHERE community_name IN (SELECT name FROM noise_communities);

-- 4. Verification Output
SELECT 'Deleted Communities' as metric, COUNT(*) as count FROM noise_communities;
SELECT 'Remaining Communities' as metric, COUNT(*) as count FROM community_pool;

COMMIT;
