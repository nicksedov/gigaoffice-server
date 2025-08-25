SELECT 
    version() as version,
    current_database() as database_name,
    current_user as current_user,
    inet_server_addr() as server_addr,
    inet_server_port() as server_port
