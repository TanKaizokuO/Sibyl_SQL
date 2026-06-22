-- ================================
-- Cognitive Database Agent - Extension Setup
-- ================================
-- Purpose: Enable PostgreSQL extensions required for vector operations
-- Extensions:
--   1. pgvector - Vector similarity search for RAG retrieval
--   2. uuid-ossp - UUID generation for primary keys
-- ================================

-- Enable pgvector extension for embedding storage and similarity search
-- This allows us to store and query vector embeddings for RAG
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID extension for generating unique identifiers
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Verify extensions are installed
SELECT
    extname AS extension_name,
    extversion AS version
FROM pg_extension
WHERE extname IN ('vector', 'uuid-ossp');

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✓ Extensions setup completed successfully';
    RAISE NOTICE '  - pgvector: Enabled for vector similarity search';
    RAISE NOTICE '  - uuid-ossp: Enabled for UUID generation';
END $$;
