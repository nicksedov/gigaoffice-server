-- LLM Input Optimizations table
CREATE TABLE IF NOT EXISTS llm_input_optimizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    original_data JSONB NOT NULL,
    optimizations_applied JSONB NOT NULL,
    optimized_data JSONB NOT NULL,
    original_size_bytes INTEGER NOT NULL,
    optimized_size_bytes INTEGER NOT NULL,
    reduction_percentage FLOAT GENERATED ALWAYS AS 
        (CASE 
            WHEN original_size_bytes > 0 
            THEN ((original_size_bytes - optimized_size_bytes)::FLOAT / original_size_bytes * 100)
            ELSE 0 
        END) STORED,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for llm_input_optimizations table
CREATE INDEX IF NOT EXISTS idx_llm_optimizations_created_at ON llm_input_optimizations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_llm_optimizations_sizes ON llm_input_optimizations(original_size_bytes, optimized_size_bytes);