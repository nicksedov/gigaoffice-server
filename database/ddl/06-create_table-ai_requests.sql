-- AI Requests table
CREATE TABLE IF NOT EXISTS ai_requests (
    id UUID PRIMARY KEY,
    user_id INTEGER,
    status VARCHAR(20) DEFAULT 'pending',
    input_range VARCHAR(50),
    query_text TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    optimization_id UUID,
    result_data JSONB,
    error_message TEXT,
    tokens_used INTEGER DEFAULT 0,
    processing_time FLOAT,
    gigachat_request_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    queue_position INTEGER,
    priority INTEGER DEFAULT 0
);

-- Create indexes for ai_requests table
CREATE INDEX IF NOT EXISTS idx_ai_requests_user_id ON ai_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_requests_status ON ai_requests(status);
CREATE INDEX IF NOT EXISTS idx_ai_requests_created_at ON ai_requests(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_requests_priority ON ai_requests(priority DESC);
CREATE INDEX IF NOT EXISTS idx_ai_requests_optimization_id ON ai_requests(optimization_id);