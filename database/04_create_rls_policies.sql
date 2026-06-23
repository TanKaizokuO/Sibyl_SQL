-- ================================
-- Cognitive Database Agent - Row-Level Security (RLS) Policies
-- ================================
-- Purpose: Enforce security at the database level BEFORE the AI agent accesses data
--
-- THEORY: Row-Level Security (RLS)
-- --------------------------------
-- RLS is a PostgreSQL feature that allows fine-grained control over which rows
-- a user can access in a table. Unlike application-level permission checks,
-- RLS is enforced by the database itself, making it impossible to bypass.
--
-- Why RLS is more secure than application-level checks:
-- 1. Defense in depth: Even if application code has bugs, DB still enforces security
-- 2. Consistent enforcement: All queries (even direct SQL) respect RLS
-- 3. No bypass: Cannot be circumvented by SQL injection or API manipulation
-- 4. Centralized: Security logic lives in one place (database), not scattered in code
--
-- Our RLS Strategy:
-- -----------------
-- 1. db_admin role: Can access ALL rows (no restrictions)
-- 2. db_manager role: Can only access rows in their assigned region
-- 3. db_viewer role: Can READ all rows but CANNOT modify/delete
--
-- ================================

-- ================================
-- CREATE DATABASE ROLES
-- ================================
-- These roles are used for role impersonation via SET LOCAL ROLE
-- The agent will switch to these roles before executing queries

-- Revoke privileges and drop roles if they exist
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'db_admin') THEN
        EXECUTE 'DROP OWNED BY db_admin;';
        EXECUTE 'DROP ROLE db_admin;';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'db_manager') THEN
        EXECUTE 'DROP OWNED BY db_manager;';
        EXECUTE 'DROP ROLE db_manager;';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'db_viewer') THEN
        EXECUTE 'DROP OWNED BY db_viewer;';
        EXECUTE 'DROP ROLE db_viewer;';
    END IF;
END $$;

-- Create roles with appropriate connection privileges
CREATE ROLE db_admin;
CREATE ROLE db_manager;
CREATE ROLE db_viewer;

-- Grant connection privileges
GRANT CONNECT ON DATABASE cognitive_db_agent TO db_admin;
GRANT CONNECT ON DATABASE cognitive_db_agent TO db_manager;
GRANT CONNECT ON DATABASE cognitive_db_agent TO db_viewer;

-- Grant schema usage
GRANT USAGE ON SCHEMA public TO db_admin, db_manager, db_viewer;

-- Grant table privileges
-- Admin: Full access
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO db_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO db_admin;

-- Manager: Read/Write on sales_data, Read-only on others
GRANT SELECT, INSERT, UPDATE, DELETE ON sales_data TO db_manager;
GRANT SELECT, INSERT, UPDATE, DELETE ON sales_archive TO db_manager;
GRANT SELECT ON users, roles, permissions, knowledge_documents TO db_manager;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO db_manager;

-- Viewer: Read-only on all tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO db_viewer;


-- ================================
-- ENABLE RLS ON TABLES
-- ================================
-- Enable RLS on sales_data (our primary test table)
ALTER TABLE sales_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales_archive ENABLE ROW LEVEL SECURITY;

-- Force RLS even for table owners (important for testing)
ALTER TABLE sales_data FORCE ROW LEVEL SECURITY;
ALTER TABLE sales_archive FORCE ROW LEVEL SECURITY;


-- ================================
-- POLICY 1: Admin Full Access
-- ================================
-- Admins can see and modify ALL rows
CREATE POLICY admin_all_access ON sales_data
    FOR ALL
    TO db_admin
    USING (true)
    WITH CHECK (true);

CREATE POLICY admin_all_access_archive ON sales_archive
    FOR ALL
    TO db_admin
    USING (true)
    WITH CHECK (true);


-- ================================
-- POLICY 2: Manager Regional Access
-- ================================
-- Managers can only access rows in their assigned region
-- This requires a helper function to determine the manager's region

-- Create function to get user's region based on their username
-- In a real system, this would query the users table
CREATE OR REPLACE FUNCTION get_user_region() RETURNS TEXT AS $$
DECLARE
    current_role_name TEXT;
BEGIN
    -- Get the current role
    SELECT current_user INTO current_role_name;

    -- For this demo, we'll use a simple mapping
    -- In production, this would query the users table
    -- based on the authenticated user's session

    -- Return NULL for admin (access all regions)
    IF current_role_name = 'db_admin' THEN
        RETURN NULL;
    END IF;

    -- For managers, we'll use session variables set by the application
    -- The application will call: SET LOCAL app.user_region = 'North';
    RETURN current_setting('app.user_region', true);
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

-- Manager SELECT policy: Can read rows in their region
CREATE POLICY manager_regional_select ON sales_data
    FOR SELECT
    TO db_manager
    USING (
        region = get_user_region()
        OR get_user_region() IS NULL
        OR current_user = 'db_admin'
    );

-- Manager INSERT policy: Can insert rows in their region
CREATE POLICY manager_regional_insert ON sales_data
    FOR INSERT
    TO db_manager
    WITH CHECK (
        region = get_user_region()
        OR get_user_region() IS NULL
        OR current_user = 'db_admin'
    );

-- Manager UPDATE policy: Can update rows in their region
CREATE POLICY manager_regional_update ON sales_data
    FOR UPDATE
    TO db_manager
    USING (
        region = get_user_region()
        OR get_user_region() IS NULL
        OR current_user = 'db_admin'
    )
    WITH CHECK (
        region = get_user_region()
        OR get_user_region() IS NULL
        OR current_user = 'db_admin'
    );

-- Manager DELETE policy: Can delete rows in their region
CREATE POLICY manager_regional_delete ON sales_data
    FOR DELETE
    TO db_manager
    USING (
        region = get_user_region()
        OR get_user_region() IS NULL
        OR current_user = 'db_admin'
    );

-- Archive table policies for managers
CREATE POLICY manager_archive_select ON sales_archive
    FOR SELECT
    TO db_manager
    USING (true);  -- Managers can read all archived data

CREATE POLICY manager_archive_insert ON sales_archive
    FOR INSERT
    TO db_manager
    WITH CHECK (
        region = get_user_region()
        OR get_user_region() IS NULL
    );


-- ================================
-- POLICY 3: Viewer Read-Only Access
-- ================================
-- Viewers can read ALL rows but cannot modify anything
CREATE POLICY viewer_readonly ON sales_data
    FOR SELECT
    TO db_viewer
    USING (true);

CREATE POLICY viewer_readonly_archive ON sales_archive
    FOR SELECT
    TO db_viewer
    USING (true);

-- Explicitly block writes for viewers (defensive programming)
CREATE POLICY viewer_block_write ON sales_data
    FOR INSERT
    TO db_viewer
    WITH CHECK (false);

CREATE POLICY viewer_block_update ON sales_data
    FOR UPDATE
    TO db_viewer
    USING (false);

CREATE POLICY viewer_block_delete ON sales_data
    FOR DELETE
    TO db_viewer
    USING (false);


-- ================================
-- VERIFY POLICIES
-- ================================
-- Display all created policies
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE tablename IN ('sales_data', 'sales_archive')
ORDER BY tablename, policyname;

-- ================================
-- Summary
-- ================================
DO $$
DECLARE
    policy_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE tablename IN ('sales_data', 'sales_archive');

    RAISE NOTICE '';
    RAISE NOTICE '════════════════════════════════════════════════════════';
    RAISE NOTICE '✓ Row-Level Security Setup Complete';
    RAISE NOTICE '════════════════════════════════════════════════════════';
    RAISE NOTICE 'Database Roles Created: db_admin, db_manager, db_viewer';
    RAISE NOTICE 'Tables with RLS:        sales_data, sales_archive';
    RAISE NOTICE 'Policies Created:       % policies', policy_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Security Model:';
    RAISE NOTICE '  • db_admin:   Full access to all rows';
    RAISE NOTICE '  • db_manager: Regional access (controlled by app.user_region)';
    RAISE NOTICE '  • db_viewer:  Read-only access to all rows';
    RAISE NOTICE '════════════════════════════════════════════════════════';
END $$;

-- ================================
-- IMPORTANT NOTES FOR DEVELOPERS
-- ================================
-- 1. Role Impersonation:
--    Before executing queries, set the role:
--    SET LOCAL ROLE db_admin;  -- or db_manager, db_viewer
--
-- 2. Regional Access for Managers:
--    Before executing as manager, set their region:
--    SET LOCAL app.user_region = 'North';  -- or South, East, West
--
-- 3. Testing RLS:
--    See 05_test_security.sql for examples of how to test policies
--
-- 4. Reset Role:
--    After testing, reset to default:
--    RESET ROLE;
-- ================================
