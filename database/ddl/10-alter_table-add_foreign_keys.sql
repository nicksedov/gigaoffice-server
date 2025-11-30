-- Add foreign key constraint for ai_requests -> llm_input_optimizations
ALTER TABLE ai_requests ADD CONSTRAINT fk_ai_requests_optimization 
    FOREIGN KEY (optimization_id) REFERENCES llm_input_optimizations(id) ON DELETE SET NULL;