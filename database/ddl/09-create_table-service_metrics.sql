-- Service Metrics table
CREATE TABLE IF NOT EXISTS service_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    total_requests INTEGER DEFAULT 0,
    successful_requests INTEGER DEFAULT 0,
    failed_requests INTEGER DEFAULT 0,
    pending_requests INTEGER DEFAULT 0,
    avg_processing_time FLOAT,
    max_processing_time FLOAT,
    min_processing_time FLOAT,
    total_tokens_used INTEGER DEFAULT 0,
    cpu_usage FLOAT,
    memory_usage FLOAT,
    disk_usage FLOAT,
    gigachat_errors INTEGER DEFAULT 0,
    gigachat_avg_response_time FLOAT
);

-- Create indexes for service_metrics table
CREATE INDEX IF NOT EXISTS idx_service_metrics_timestamp ON service_metrics(timestamp DESC);