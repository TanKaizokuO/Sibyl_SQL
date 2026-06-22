-- ================================
-- Cognitive Database Agent - Sample Data
-- ================================
-- Purpose: Insert sample data for testing and demonstration
-- Data includes:
--   - 3 roles (Admin, Manager, Viewer)
--   - Sample users for each role
--   - Permission matrix for each role
--   - Sales data across multiple years and regions
-- ================================

-- ================================
-- 1. INSERT ROLES
-- ================================
INSERT INTO roles (role_name, description) VALUES
    ('db_admin', 'Full access to all data and operations. Can view, modify, and delete any record.'),
    ('db_manager', 'Regional manager access. Can view and modify data in their assigned region only.'),
    ('db_viewer', 'Read-only access. Can view data but cannot modify or delete anything.');

-- ================================
-- 2. INSERT USERS
-- ================================
-- Create sample users for each role
INSERT INTO users (username, email, role_name) VALUES
    -- Admin users
    ('admin', 'admin@cognitivdb.com', 'db_admin'),
    ('alice_admin', 'alice@cognitivdb.com', 'db_admin'),

    -- Manager users
    ('bob_manager_north', 'bob@cognitivdb.com', 'db_manager'),
    ('carol_manager_south', 'carol@cognitivdb.com', 'db_manager'),
    ('dave_manager_east', 'dave@cognitivdb.com', 'db_manager'),
    ('eve_manager_west', 'eve@cognitivdb.com', 'db_manager'),

    -- Viewer users
    ('viewer', 'viewer@cognitivdb.com', 'db_viewer'),
    ('frank_viewer', 'frank@cognitivdb.com', 'db_viewer');

-- ================================
-- 3. INSERT PERMISSIONS
-- ================================
-- Admin: Full access to everything
INSERT INTO permissions (role_name, resource, can_read, can_write, can_update, can_delete) VALUES
    ('db_admin', 'sales_data', true, true, true, true),
    ('db_admin', 'sales_archive', true, true, true, true),
    ('db_admin', 'knowledge_documents', true, true, true, true),
    ('db_admin', 'users', true, true, true, true),
    ('db_admin', 'roles', true, true, true, true);

-- Manager: Can read and modify sales_data in their region, read-only on archive
INSERT INTO permissions (role_name, resource, can_read, can_write, can_update, can_delete) VALUES
    ('db_manager', 'sales_data', true, true, true, true),
    ('db_manager', 'sales_archive', true, false, false, false),
    ('db_manager', 'knowledge_documents', true, false, false, false);

-- Viewer: Read-only access to sales data and knowledge base
INSERT INTO permissions (role_name, resource, can_read, can_write, can_update, can_delete) VALUES
    ('db_viewer', 'sales_data', true, false, false, false),
    ('db_viewer', 'sales_archive', true, false, false, false),
    ('db_viewer', 'knowledge_documents', true, false, false, false);

-- ================================
-- 4. INSERT SALES DATA
-- ================================
-- Get user IDs for assignment
DO $$
DECLARE
    admin_id UUID;
    bob_id UUID;
    carol_id UUID;
    dave_id UUID;
    eve_id UUID;
BEGIN
    -- Get user IDs
    SELECT id INTO admin_id FROM users WHERE username = 'admin';
    SELECT id INTO bob_id FROM users WHERE username = 'bob_manager_north';
    SELECT id INTO carol_id FROM users WHERE username = 'carol_manager_south';
    SELECT id INTO dave_id FROM users WHERE username = 'dave_manager_east';
    SELECT id INTO eve_id FROM users WHERE username = 'eve_manager_west';

    -- Insert sales data for 2021
    INSERT INTO sales_data (year, quarter, amount, region, product, user_id) VALUES
        -- North region (Bob's data)
        (2021, 1, 150000.00, 'North', 'Product A', bob_id),
        (2021, 2, 175000.00, 'North', 'Product A', bob_id),
        (2021, 3, 160000.00, 'North', 'Product B', bob_id),
        (2021, 4, 190000.00, 'North', 'Product B', bob_id),

        -- South region (Carol's data)
        (2021, 1, 120000.00, 'South', 'Product A', carol_id),
        (2021, 2, 135000.00, 'South', 'Product A', carol_id),
        (2021, 3, 145000.00, 'South', 'Product C', carol_id),
        (2021, 4, 155000.00, 'South', 'Product C', carol_id),

        -- East region (Dave's data)
        (2021, 1, 180000.00, 'East', 'Product B', dave_id),
        (2021, 2, 195000.00, 'East', 'Product B', dave_id),
        (2021, 3, 185000.00, 'East', 'Product A', dave_id),
        (2021, 4, 210000.00, 'East', 'Product A', dave_id),

        -- West region (Eve's data)
        (2021, 1, 165000.00, 'West', 'Product C', eve_id),
        (2021, 2, 170000.00, 'West', 'Product C', eve_id),
        (2021, 3, 180000.00, 'West', 'Product A', eve_id),
        (2021, 4, 200000.00, 'West', 'Product A', eve_id);

    -- Insert sales data for 2022
    INSERT INTO sales_data (year, quarter, amount, region, product, user_id) VALUES
        -- North region
        (2022, 1, 200000.00, 'North', 'Product A', bob_id),
        (2022, 2, 225000.00, 'North', 'Product A', bob_id),
        (2022, 3, 210000.00, 'North', 'Product B', bob_id),
        (2022, 4, 240000.00, 'North', 'Product B', bob_id),

        -- South region
        (2022, 1, 170000.00, 'South', 'Product A', carol_id),
        (2022, 2, 185000.00, 'South', 'Product A', carol_id),
        (2022, 3, 195000.00, 'South', 'Product C', carol_id),
        (2022, 4, 205000.00, 'South', 'Product C', carol_id),

        -- East region
        (2022, 1, 230000.00, 'East', 'Product B', dave_id),
        (2022, 2, 245000.00, 'East', 'Product B', dave_id),
        (2022, 3, 235000.00, 'East', 'Product A', dave_id),
        (2022, 4, 260000.00, 'East', 'Product A', dave_id),

        -- West region
        (2022, 1, 215000.00, 'West', 'Product C', eve_id),
        (2022, 2, 220000.00, 'West', 'Product C', eve_id),
        (2022, 3, 230000.00, 'West', 'Product A', eve_id),
        (2022, 4, 250000.00, 'West', 'Product A', eve_id);

    -- Insert sales data for 2023
    INSERT INTO sales_data (year, quarter, amount, region, product, user_id) VALUES
        -- North region
        (2023, 1, 250000.00, 'North', 'Product A', bob_id),
        (2023, 2, 275000.00, 'North', 'Product A', bob_id),
        (2023, 3, 260000.00, 'North', 'Product B', bob_id),
        (2023, 4, 290000.00, 'North', 'Product B', bob_id),

        -- South region
        (2023, 1, 220000.00, 'South', 'Product A', carol_id),
        (2023, 2, 235000.00, 'South', 'Product A', carol_id),
        (2023, 3, 245000.00, 'South', 'Product C', carol_id),
        (2023, 4, 255000.00, 'South', 'Product C', carol_id),

        -- East region
        (2023, 1, 280000.00, 'East', 'Product B', dave_id),
        (2023, 2, 295000.00, 'East', 'Product B', dave_id),
        (2023, 3, 285000.00, 'East', 'Product A', dave_id),
        (2023, 4, 310000.00, 'East', 'Product A', dave_id),

        -- West region
        (2023, 1, 265000.00, 'West', 'Product C', eve_id),
        (2023, 2, 270000.00, 'West', 'Product C', eve_id),
        (2023, 3, 280000.00, 'West', 'Product A', eve_id),
        (2023, 4, 300000.00, 'West', 'Product A', eve_id);

    RAISE NOTICE '✓ Inserted 48 sales records (2021-2023, 4 regions, 4 quarters each)';
END $$;

-- ================================
-- 5. INSERT KNOWLEDGE DOCUMENTS
-- ================================
-- These documents will be used by the RAG system
-- Note: Embeddings will be populated by the backend ingestion script
INSERT INTO knowledge_documents (content, doc_type, metadata) VALUES
    -- Schema descriptions
    (
        'The sales_data table contains sales information with the following columns: id (UUID primary key), year (integer), quarter (1-4), amount (decimal), region (text), product (text), user_id (foreign key to users), created_at (timestamp), updated_at (timestamp). This table is used to track sales performance across different regions and time periods.',
        'schema',
        '{"table": "sales_data", "columns": ["id", "year", "quarter", "amount", "region", "product", "user_id", "created_at", "updated_at"]}'
    ),
    (
        'The sales_archive table mirrors the sales_data structure but includes additional fields: original_id (reference to sales_data), archived_at (timestamp), archived_by (text). Use this table to store historical sales records that have been archived.',
        'schema',
        '{"table": "sales_archive", "columns": ["id", "original_id", "year", "quarter", "amount", "region", "product", "user_id", "archived_at", "archived_by"]}'
    ),
    (
        'The users table stores user account information: id (UUID), username (unique text), email (unique text), role_name (foreign key to roles), is_active (boolean), created_at (timestamp), updated_at (timestamp). Each user is assigned exactly one role.',
        'schema',
        '{"table": "users", "columns": ["id", "username", "email", "role_name", "is_active", "created_at", "updated_at"]}'
    ),
    (
        'The roles table defines available roles: role_name (primary key text), description (text), created_at (timestamp). Available roles are: db_admin (full access), db_manager (regional access), db_viewer (read-only).',
        'schema',
        '{"table": "roles", "columns": ["role_name", "description", "created_at"]}'
    ),

    -- Example queries
    (
        'To find total sales for a specific year, use: SELECT SUM(amount) FROM sales_data WHERE year = [year_number]. For example, to get 2022 sales: SELECT SUM(amount) FROM sales_data WHERE year = 2022.',
        'example_query',
        '{"operation": "aggregate", "function": "SUM", "table": "sales_data"}'
    ),
    (
        'To archive old sales data, perform these steps: 1) SELECT the records to archive, 2) INSERT them into sales_archive with archived_at and archived_by, 3) DELETE from sales_data. Always wrap this in a transaction for data integrity.',
        'example_query',
        '{"operation": "archive", "tables": ["sales_data", "sales_archive"], "steps": 3}'
    ),
    (
        'To query sales by region, use: SELECT * FROM sales_data WHERE region = [region_name]. Valid regions are: North, South, East, West.',
        'example_query',
        '{"operation": "filter", "column": "region", "table": "sales_data", "valid_values": ["North", "South", "East", "West"]}'
    ),

    -- Policy information
    (
        'Row-Level Security (RLS) is enabled on sales_data. Admin users can access all records. Manager users can only access records in their assigned region. Viewer users can read all records but cannot modify any data.',
        'policy',
        '{"table": "sales_data", "rls_enabled": true, "policies": ["admin_all_access", "manager_regional_access", "viewer_readonly"]}'
    );

-- ================================
-- Summary
-- ================================
DO $$
DECLARE
    role_count INTEGER;
    user_count INTEGER;
    permission_count INTEGER;
    sales_count INTEGER;
    knowledge_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO role_count FROM roles;
    SELECT COUNT(*) INTO user_count FROM users;
    SELECT COUNT(*) INTO permission_count FROM permissions;
    SELECT COUNT(*) INTO sales_count FROM sales_data;
    SELECT COUNT(*) INTO knowledge_count FROM knowledge_documents;

    RAISE NOTICE '';
    RAISE NOTICE '════════════════════════════════════════════════════════';
    RAISE NOTICE '✓ Sample Data Insertion Complete';
    RAISE NOTICE '════════════════════════════════════════════════════════';
    RAISE NOTICE 'Roles:                % records', role_count;
    RAISE NOTICE 'Users:                % records', user_count;
    RAISE NOTICE 'Permissions:          % records', permission_count;
    RAISE NOTICE 'Sales Data:           % records', sales_count;
    RAISE NOTICE 'Knowledge Documents:  % records', knowledge_count;
    RAISE NOTICE '════════════════════════════════════════════════════════';
END $$;
