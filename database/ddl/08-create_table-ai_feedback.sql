-- AI Feedback table
CREATE TABLE IF NOT EXISTS ai_feedback (
    id SERIAL PRIMARY KEY,
    ai_request_id UUID NOT NULL REFERENCES ai_requests(id) ON DELETE CASCADE,
    text_response TEXT NOT NULL,
    rating BOOLEAN,
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for ai_feedback table
CREATE INDEX idx_ai_responses_request_id ON ai_feedback(ai_request_id);