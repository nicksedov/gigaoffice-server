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