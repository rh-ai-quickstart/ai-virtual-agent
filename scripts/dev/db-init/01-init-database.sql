-- AI Virtual Agent Database Initialization Script
-- This script runs automatically when PostgreSQL container starts for the first time
-- No manual intervention required!

\echo '🚀 Starting AI Virtual Agent database initialization...'

-- Connect to the ai_virtual_agent database (already created by POSTGRES_DB)
\c ai_virtual_agent;

-- Note: UUID generation uses Python's uuid.uuid4(), no extension needed
-- Note: No text search features requiring pg_trgm are currently used

-- Grant comprehensive permissions to the admin user
GRANT ALL PRIVILEGES ON DATABASE ai_virtual_agent TO admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO admin;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO admin;

-- Set default privileges for future objects created by any user
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO admin;

\echo '✓ Database permissions configured'

-- Create a verification function
CREATE OR REPLACE FUNCTION verify_database_setup() RETURNS TABLE(
    component TEXT,
    status TEXT,
    details TEXT
) AS $$
BEGIN
    -- Test basic database connectivity
    RETURN QUERY SELECT 'Database Connection'::TEXT, 'OK'::TEXT, 'Connected successfully'::TEXT;
    
    -- Test permissions
    BEGIN
        CREATE TEMP TABLE test_permissions (id SERIAL);
        DROP TABLE test_permissions;
        RETURN QUERY SELECT 'Database Permissions'::TEXT, 'OK'::TEXT, 'Write permissions verified'::TEXT;
    EXCEPTION WHEN others THEN
        RETURN QUERY SELECT 'Database Permissions'::TEXT, 'ERROR'::TEXT, SQLERRM::TEXT;
    END;
    
    RETURN QUERY SELECT 'Database Setup'::TEXT, 'COMPLETE'::TEXT, 
                       ('Initialized at ' || NOW()::TEXT)::TEXT;
END;
$$ LANGUAGE plpgsql;

-- Run verification and display results
\echo ''
\echo '🔍 Verifying database setup:'
SELECT * FROM verify_database_setup();

\echo ''
\echo '🎉 AI Virtual Agent database is ready!'