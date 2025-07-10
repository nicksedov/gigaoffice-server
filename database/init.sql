-- GigaOffice Database Initialization Script
-- Скрипт инициализации базы данных для GigaOffice

-- Create database (if not exists)
-- This will be handled by Docker environment variables

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create custom types
DO $$ BEGIN
    CREATE TYPE request_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('user', 'admin', 'premium');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create tables (will also be handled by SQLAlchemy, but included for reference)

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(20) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    last_login TIMESTAMP WITH TIME ZONE,
    total_requests INTEGER DEFAULT 0,
    total_tokens_used INTEGER DEFAULT 0,
    monthly_requests INTEGER DEFAULT 0,
    monthly_tokens_used INTEGER DEFAULT 0
);

-- Prompts table
CREATE TABLE IF NOT EXISTS prompts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    template TEXT NOT NULL,
    category VARCHAR(100),
    language VARCHAR(10) DEFAULT 'ru',
    is_active BOOLEAN DEFAULT TRUE,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by INTEGER
);

-- AI Requests table
CREATE TABLE IF NOT EXISTS ai_requests (
    id UUID PRIMARY KEY,
    user_id INTEGER,
    status VARCHAR(20) DEFAULT 'pending',
    input_range VARCHAR(50),
    output_range VARCHAR(50) NOT NULL,
    query_text TEXT NOT NULL,
    preset_prompt_id INTEGER,
    input_data JSONB,
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

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

CREATE INDEX IF NOT EXISTS idx_prompts_language ON prompts(language);
CREATE INDEX IF NOT EXISTS idx_prompts_category ON prompts(category);
CREATE INDEX IF NOT EXISTS idx_prompts_is_active ON prompts(is_active);
CREATE INDEX IF NOT EXISTS idx_prompts_usage_count ON prompts(usage_count DESC);

CREATE INDEX IF NOT EXISTS idx_ai_requests_user_id ON ai_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_requests_status ON ai_requests(status);
CREATE INDEX IF NOT EXISTS idx_ai_requests_created_at ON ai_requests(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_requests_priority ON ai_requests(priority DESC);

CREATE INDEX IF NOT EXISTS idx_service_metrics_timestamp ON service_metrics(timestamp DESC);

-- Create foreign key constraints
-- (These will be handled by SQLAlchemy, but included for completeness)

-- Insert default data
INSERT INTO users (username, email, hashed_password, full_name, role) 
VALUES 
    ('admin', 'admin@gigaoffice.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewFyrtDJejt9Z3Im', 'System Administrator', 'admin'),
    ('demo', 'demo@gigaoffice.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewFyrtDJejt9Z3Im', 'Demo User', 'user')
ON CONFLICT (username) DO NOTHING;

-- Create functions for common operations

-- Function to update user statistics
CREATE OR REPLACE FUNCTION update_user_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        UPDATE users 
        SET 
            total_requests = total_requests + 1,
            total_tokens_used = total_tokens_used + COALESCE(NEW.tokens_used, 0),
            monthly_requests = monthly_requests + 1,
            monthly_tokens_used = monthly_tokens_used + COALESCE(NEW.tokens_used, 0)
        WHERE id = NEW.user_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for updating user stats
DROP TRIGGER IF EXISTS trigger_update_user_stats ON ai_requests;
CREATE TRIGGER trigger_update_user_stats
    AFTER UPDATE ON ai_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_user_stats();

-- Function to clean old metrics
CREATE OR REPLACE FUNCTION clean_old_metrics()
RETURNS void AS $$
BEGIN
    -- Keep only last 90 days of metrics
    DELETE FROM service_metrics 
    WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '90 days';
    
    -- Keep only last 365 days of completed requests
    DELETE FROM ai_requests 
    WHERE status = 'completed' 
    AND completed_at < CURRENT_TIMESTAMP - INTERVAL '365 days';
END;
$$ LANGUAGE plpgsql;

-- Function to get service statistics
CREATE OR REPLACE FUNCTION get_service_stats(period_hours INTEGER DEFAULT 24)
RETURNS TABLE (
    total_requests BIGINT,
    successful_requests BIGINT,
    failed_requests BIGINT,
    avg_processing_time FLOAT,
    total_tokens BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) as total_requests,
        COUNT(*) FILTER (WHERE status = 'completed') as successful_requests,
        COUNT(*) FILTER (WHERE status = 'failed') as failed_requests,
        AVG(processing_time) as avg_processing_time,
        SUM(tokens_used)::BIGINT as total_tokens
    FROM ai_requests
    WHERE created_at >= CURRENT_TIMESTAMP - (period_hours || ' hours')::INTERVAL;
END;
$$ LANGUAGE plpgsql;

-- Create view for user dashboard
CREATE OR REPLACE VIEW user_dashboard AS
SELECT 
    u.id,
    u.username,
    u.email,
    u.full_name,
    u.role,
    u.total_requests,
    u.total_tokens_used,
    u.last_login,
    COUNT(ar.id) FILTER (WHERE ar.created_at >= CURRENT_DATE) as requests_today,
    COUNT(ar.id) FILTER (WHERE ar.status = 'completed' AND ar.created_at >= CURRENT_DATE) as completed_today,
    AVG(ar.processing_time) FILTER (WHERE ar.status = 'completed' AND ar.created_at >= CURRENT_DATE) as avg_time_today
FROM users u
LEFT JOIN ai_requests ar ON u.id = ar.user_id
GROUP BY u.id, u.username, u.email, u.full_name, u.role, u.total_requests, u.total_tokens_used, u.last_login;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA gigaoffice TO gigaoffice;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA gigaoffice TO gigaoffice;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA gigaoffice TO gigaoffice;

-- Log completion
INSERT INTO service_metrics (
    total_requests, successful_requests, failed_requests, pending_requests
) VALUES (0, 0, 0, 0);

-- Create notification for application
NOTIFY gigaoffice_init_complete;