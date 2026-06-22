-- ================================
-- Cognitive Database Agent - Auth Users Table Setup
-- ================================
-- Purpose: Create table for authenticated users and seed demo accounts
-- ================================

CREATE TABLE auth_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL REFERENCES roles(role_name) ON DELETE RESTRICT,
    region VARCHAR(50) NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE auth_users IS 'Authenticated users for the Cognitive Database Agent application';
COMMENT ON COLUMN auth_users.role IS 'System role assigned to user (references roles table)';
COMMENT ON COLUMN auth_users.region IS 'Assigned region for manager role (e.g. North, South, East, West)';

-- Create indexes for performance
CREATE INDEX idx_auth_users_username ON auth_users(username);
CREATE INDEX idx_auth_users_role ON auth_users(role);

-- Seed demo users
-- Passwords:
--   admin_user: admin123
--   north_manager: manager123
--   viewer_user: viewer123
INSERT INTO auth_users (username, email, password_hash, role, region) VALUES
    ('admin_user', 'admin@cognitivedb.com', '$2b$12$LAWXqRvyXhiePOiUY0kS8uv0p0C2bwqTNbC/kc8XYJe5Ck7S6m0QK', 'db_admin', NULL),
    ('north_manager', 'manager@cognitivedb.com', '$2b$12$KuwLlYpIfHZkyZzMTpMwUuVm4RixDHdUCysAMsPAx0GyJ0iXCOH0O', 'db_manager', 'North'),
    ('viewer_user', 'viewer@cognitivedb.com', '$2b$12$FYGZSxsiDabMvnkZ1JOkHOwmgzC3ENBIxV5/5P0.IAeo7xBR7QNqm', 'db_viewer', NULL);
