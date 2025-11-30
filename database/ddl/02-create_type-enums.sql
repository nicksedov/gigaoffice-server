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