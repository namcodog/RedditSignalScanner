-- Migration: Introduce Business Categories & Tagging System
-- Date: 2025-12-02
-- Objective: Normalize categories into a relational tagging system while preserving existing data.

BEGIN;

-- 1. Create the Master Category Dictionary (Tag Library)
CREATE TABLE IF NOT EXISTS business_categories (
    key VARCHAR(50) PRIMARY KEY,  -- e.g., 'E-commerce_Ops', 'Home_Lifestyle'
    display_name VARCHAR(100),    -- e.g., '跨境电商运营'
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE business_categories IS '权威业务分类字典表，强制唯一定义';

-- 2. Create the Mapping Table (Many-to-Many)
CREATE TABLE IF NOT EXISTS community_category_map (
    community_id INTEGER NOT NULL,
    category_key VARCHAR(50) NOT NULL,
    is_primary BOOLEAN DEFAULT false, -- Is this the main category for the community?
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    PRIMARY KEY (community_id, category_key),
    
    CONSTRAINT fk_map_community 
        FOREIGN KEY (community_id) 
        REFERENCES community_pool(id) 
        ON DELETE CASCADE,
        
    CONSTRAINT fk_map_category 
        FOREIGN KEY (category_key) 
        REFERENCES business_categories(key) 
        ON DELETE CASCADE
);

COMMENT ON TABLE community_category_map IS '社区与业务分类的关联表 (打标)';

-- 3. Initial Data Seeding (Standard Tags from current system)
INSERT INTO business_categories (key, display_name) VALUES
('E-commerce_Ops', 'E-commerce Operations'),
('Home_Lifestyle', 'Home & Lifestyle'),
('Family_Parenting', 'Family & Parenting'),
('Tools_EDC', 'Tools & EDC'),
('Food_Coffee_Lifestyle', 'Food, Coffee & Lifestyle'),
('Minimal_Outdoor', 'Minimalism & Outdoor'),
('Frugal_Living', 'Frugal Living'),
('High_Value', 'High Value Community'),
('Recovered', 'Recovered from Disaster'),
('Competitor', 'Competitor Watchlist')
ON CONFLICT (key) DO NOTHING;

COMMIT;
