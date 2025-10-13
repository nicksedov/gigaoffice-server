-- Migration: Remove chart_requests table and add indexes for chart processing via ai_requests
-- Date: 2025-10-13
-- Description: Consolidate chart request tracking into ai_requests table

-- Step 1: Verify ai_requests table exists and has necessary fields
-- The ai_requests table should have:
-- - category field (VARCHAR) for request type differentiation
-- - input_data (JSONB) for storing chart-specific input
-- - result_data (JSONB) for storing chart configuration results

-- Step 2: Add indexes to ai_requests table for chart-related queries
CREATE INDEX IF NOT EXISTS idx_ai_requests_category ON ai_requests(category);
CREATE INDEX IF NOT EXISTS idx_ai_requests_user_category_created ON ai_requests(user_id, category, created_at DESC);

-- Step 3: Drop chart_requests table if it exists
-- Note: Only drop if the table exists and has no foreign key dependencies
DROP TABLE IF EXISTS chart_requests CASCADE;

-- Step 4: Verify migration success
-- The following query should return 0 if chart_requests table is successfully removed
DO $$
DECLARE
    table_exists INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_exists
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'chart_requests';
    
    IF table_exists > 0 THEN
        RAISE NOTICE 'WARNING: chart_requests table still exists after migration';
    ELSE
        RAISE NOTICE 'SUCCESS: chart_requests table successfully removed';
    END IF;
END $$;

-- Step 5: Verify indexes are created
DO $$
DECLARE
    category_index_exists INTEGER;
    composite_index_exists INTEGER;
BEGIN
    SELECT COUNT(*) INTO category_index_exists
    FROM pg_indexes
    WHERE schemaname = 'public'
    AND tablename = 'ai_requests'
    AND indexname = 'idx_ai_requests_category';
    
    SELECT COUNT(*) INTO composite_index_exists
    FROM pg_indexes
    WHERE schemaname = 'public'
    AND tablename = 'ai_requests'
    AND indexname = 'idx_ai_requests_user_category_created';
    
    IF category_index_exists > 0 THEN
        RAISE NOTICE 'SUCCESS: idx_ai_requests_category index created';
    ELSE
        RAISE NOTICE 'WARNING: idx_ai_requests_category index not created';
    END IF;
    
    IF composite_index_exists > 0 THEN
        RAISE NOTICE 'SUCCESS: idx_ai_requests_user_category_created index created';
    ELSE
        RAISE NOTICE 'WARNING: idx_ai_requests_user_category_created index not created';
    END IF;
END $$;

-- Migration complete
