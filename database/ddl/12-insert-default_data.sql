-- Insert default data
INSERT INTO users (username, email, hashed_password, full_name, role) 
VALUES 
    ('admin', 'admin@gigaoffice.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewFyrtDJejt9Z3Im', 'System Administrator', 'admin'),
    ('demo', 'demo@gigaoffice.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewFyrtDJejt9Z3Im', 'Demo User', 'user')
ON CONFLICT (username) DO NOTHING;

-- Log completion
INSERT INTO service_metrics (
    total_requests, successful_requests, failed_requests, pending_requests
) VALUES (0, 0, 0, 0);

-- Create notification for application
NOTIFY gigaoffice_init_complete;