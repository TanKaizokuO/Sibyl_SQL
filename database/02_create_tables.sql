-- ================================
-- Cognitive Database Agent - Schema Definition
-- ================================
-- Purpose: Create all tables for the cognitive database system
-- Tables:
--   1. roles - Define available roles (Admin, Manager, Viewer)
--   2. users - User accounts with role assignments
--   3. permissions - Fine-grained permissions per role
--   4. sales_data - Sample business data for testing RLS
--   5. sales_archive - Archive table for testing multi-step operations
--   6. knowledge_documents - RAG knowledge base with vector embeddings
-- ================================

-- Drop existing tables if they exist (for development)
DROP TABLE IF EXISTS knowledge_documents CASCADE;
DROP TABLE IF EXISTS sales_archive CASCADE;
DROP TABLE IF EXISTS sales_data CASCADE;
DROP TABLE IF EXISTS permissions CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS roles CASCADE;

-- ================================
-- 1. ROLES TABLE
-- ================================
-- Defines the available roles in the system
-- Each role has different levels of access to data
CREATE TABLE roles (
    role_name VARCHAR(50) PRIMARY KEY,
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE roles IS 'Defines available system roles for RBAC';
COMMENT ON COLUMN roles.role_name IS 'Unique identifier for the role (e.g., db_admin, db_manager, db_viewer)';
COMMENT ON COLUMN roles.description IS 'Human-readable description of role capabilities';

-- ================================
-- 2. USERS TABLE
-- ================================
-- Stores user accounts and their role assignments
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role_name VARCHAR(50) NOT NULL REFERENCES roles(role_name) ON DELETE RESTRICT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE users IS 'User accounts with role assignments';
COMMENT ON COLUMN users.role_name IS 'Foreign key to roles table - determines user permissions';
COMMENT ON COLUMN users.is_active IS 'Whether the user account is active';

-- Create index for faster role lookups
CREATE INDEX idx_users_role_name ON users(role_name);
CREATE INDEX idx_users_username ON users(username);

-- ================================
-- 3. PERMISSIONS TABLE
-- ================================
-- Fine-grained permissions matrix
-- Defines what each role can do on each resource
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role_name VARCHAR(50) NOT NULL REFERENCES roles(role_name) ON DELETE CASCADE,
    resource VARCHAR(100) NOT NULL,
    can_read BOOLEAN DEFAULT false,
    can_write BOOLEAN DEFAULT false,
    can_update BOOLEAN DEFAULT false,
    can_delete BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(role_name, resource)
);

COMMENT ON TABLE permissions IS 'Fine-grained permission matrix for role-based access control';
COMMENT ON COLUMN permissions.resource IS 'Resource identifier (e.g., sales_data, knowledge_documents)';
COMMENT ON COLUMN permissions.can_read IS 'Permission to SELECT data';
COMMENT ON COLUMN permissions.can_write IS 'Permission to INSERT data';
COMMENT ON COLUMN permissions.can_update IS 'Permission to UPDATE data';
COMMENT ON COLUMN permissions.can_delete IS 'Permission to DELETE data';

-- ================================
-- 4. SALES_DATA TABLE
-- ================================
-- Sample business data for demonstrating RLS policies
-- Each row has a user_id and region for access control
CREATE TABLE sales_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    year INTEGER NOT NULL,
    quarter INTEGER CHECK (quarter BETWEEN 1 AND 4),
    amount DECIMAL(15, 2) NOT NULL,
    region VARCHAR(50) NOT NULL,
    product VARCHAR(100),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE sales_data IS 'Sample sales data for testing RLS policies';
COMMENT ON COLUMN sales_data.user_id IS 'Owner of this sales record - used for RLS policy';
COMMENT ON COLUMN sales_data.region IS 'Geographic region - used for manager-level RLS';

-- Create indexes for common queries
CREATE INDEX idx_sales_data_year ON sales_data(year);
CREATE INDEX idx_sales_data_region ON sales_data(region);
CREATE INDEX idx_sales_data_user_id ON sales_data(user_id);

-- ================================
-- 5. SALES_ARCHIVE TABLE
-- ================================
-- Archive table for testing multi-step agent operations
-- Structure mirrors sales_data
CREATE TABLE sales_archive (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    original_id UUID,
    year INTEGER NOT NULL,
    quarter INTEGER CHECK (quarter BETWEEN 1 AND 4),
    amount DECIMAL(15, 2) NOT NULL,
    region VARCHAR(50) NOT NULL,
    product VARCHAR(100),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    archived_by VARCHAR(100)
);

COMMENT ON TABLE sales_archive IS 'Archive of sales data - used for multi-step operation testing';
COMMENT ON COLUMN sales_archive.original_id IS 'Reference to original sales_data.id before archival';
COMMENT ON COLUMN sales_archive.archived_at IS 'Timestamp when data was archived';
COMMENT ON COLUMN sales_archive.archived_by IS 'User/role who performed the archival';

CREATE INDEX idx_sales_archive_year ON sales_archive(year);
CREATE INDEX idx_sales_archive_original_id ON sales_archive(original_id);

-- ================================
-- 6. KNOWLEDGE_DOCUMENTS TABLE
-- ================================
-- RAG knowledge base with vector embeddings
-- Stores schema information and example queries for agent retrieval
CREATE TABLE knowledge_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content TEXT NOT NULL,
    embedding vector(384),  -- sentence-transformers all-MiniLM-L6-v2 produces 384-dimensional vectors
    metadata JSONB,
    doc_type VARCHAR(50),  -- e.g., 'schema', 'example_query', 'policy'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE knowledge_documents IS 'RAG knowledge base with vector embeddings for semantic search';
COMMENT ON COLUMN knowledge_documents.content IS 'Natural language text describing schema or examples';
COMMENT ON COLUMN knowledge_documents.embedding IS 'Vector embedding for similarity search (384 dimensions, sentence-transformers)';
COMMENT ON COLUMN knowledge_documents.metadata IS 'Additional metadata (table names, column names, etc.)';
COMMENT ON COLUMN knowledge_documents.doc_type IS 'Type of document for filtering retrieval';

-- Create index for vector similarity search
CREATE INDEX idx_knowledge_embedding ON knowledge_documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create index for document type filtering
CREATE INDEX idx_knowledge_doc_type ON knowledge_documents(doc_type);

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✓ All tables created successfully';
    RAISE NOTICE '  - roles: Role definitions';
    RAISE NOTICE '  - users: User accounts with role assignments';
    RAISE NOTICE '  - permissions: Permission matrix';
    RAISE NOTICE '  - sales_data: Sample business data';
    RAISE NOTICE '  - sales_archive: Archive table';
    RAISE NOTICE '  - knowledge_documents: RAG knowledge base';
END $$;
