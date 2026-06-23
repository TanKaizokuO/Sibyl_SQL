-- ================================
-- Cognitive Database Agent - Audit Log Table Setup
-- ================================
-- Purpose: Create audit_log table for query compliance and execution tracking
-- ================================

-- Drop existing table if it exists
DROP TABLE IF EXISTS audit_log CASCADE;

CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID,                 -- from JWT (NULL for unauthenticated or system)
    role VARCHAR(50),             -- role used for execution (e.g. admin, manager, viewer)
    region VARCHAR(50),           -- region context
    action VARCHAR(20),           -- 'SELECT', 'INSERT', 'UPDATE', 'DELETE', etc.
    tool_name VARCHAR(50),        -- which agent tool was used
    sql_query TEXT,               -- the actual SQL executed
    row_count INTEGER,            -- rows returned/affected
    success BOOLEAN,              -- did it succeed?
    error_message TEXT,           -- error if failed
    execution_time_ms INTEGER,    -- how long it took
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance Indexes
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);
CREATE INDEX idx_audit_log_role ON audit_log(role);
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);

COMMENT ON TABLE audit_log IS 'Compliance audit trail of queries executed by the agent';
COMMENT ON COLUMN audit_log.user_id IS 'ID of the authenticated user who initiated the query';
COMMENT ON COLUMN audit_log.role IS 'Database/system role used for the execution';
COMMENT ON COLUMN audit_log.action IS 'Database action type (SELECT/INSERT/UPDATE/DELETE)';
COMMENT ON COLUMN audit_log.sql_query IS 'The raw SQL query text compiled/executed';
