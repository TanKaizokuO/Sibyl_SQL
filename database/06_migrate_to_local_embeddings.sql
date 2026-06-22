-- ================================
-- Migration: Switch to Local Embeddings (sentence-transformers)
-- ================================
-- Purpose: Update vector dimension from 768 (Gemini) to 384 (sentence-transformers)
--
-- This migration:
-- 1. Drops existing embeddings (they were from Gemini anyway)
-- 2. Alters the vector column dimension from 768 to 384
-- 3. Drops and recreates the vector index
--
-- Run this BEFORE running the knowledge ingestion script with sentence-transformers
-- ================================

-- ================================
-- 1. Clear existing embeddings
-- ================================
-- These were generated with Gemini (768 dimensions) and won't work with sentence-transformers (384 dimensions)
DO $$
DECLARE
    doc_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO doc_count FROM knowledge_documents;

    IF doc_count > 0 THEN
        RAISE NOTICE 'Clearing % existing documents with 768-dimensional embeddings...', doc_count;
        TRUNCATE TABLE knowledge_documents;
        RAISE NOTICE '[OK] Cleared knowledge_documents table';
    ELSE
        RAISE NOTICE '[OK] knowledge_documents table is already empty';
    END IF;
END $$;

-- ================================
-- 2. Drop existing vector index
-- ================================
DROP INDEX IF EXISTS idx_knowledge_embedding;

-- ================================
-- 3. Alter vector column dimension
-- ================================
-- Change from vector(768) to vector(384)
ALTER TABLE knowledge_documents
    ALTER COLUMN embedding TYPE vector(384);

-- ================================
-- 4. Recreate vector index for new dimension
-- ================================
CREATE INDEX idx_knowledge_embedding
    ON knowledge_documents
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ================================
-- 5. Update column comment
-- ================================
COMMENT ON COLUMN knowledge_documents.embedding IS 'Vector embedding for similarity search (384 dimensions, sentence-transformers all-MiniLM-L6-v2)';

-- ================================
-- Summary
-- ================================
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '[OK] Migration Complete: Switched to Local Embeddings';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Embedding Model:      sentence-transformers (all-MiniLM-L6-v2)';
    RAISE NOTICE 'Vector Dimension:     384 (changed from 768)';
    RAISE NOTICE 'API Keys Required:    None';
    RAISE NOTICE 'Quota Limits:         None';
    RAISE NOTICE '';
    RAISE NOTICE 'Next Steps:';
    RAISE NOTICE '  1. Install sentence-transformers: uv pip install sentence-transformers';
    RAISE NOTICE '  2. Run knowledge ingestion: uv run python backend\scripts\ingest_knowledge.py';
    RAISE NOTICE '============================================================';
END $$;
