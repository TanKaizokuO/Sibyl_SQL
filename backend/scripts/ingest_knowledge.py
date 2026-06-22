#!/usr/bin/env python3
"""
Cognitive Database Agent - Knowledge Base Ingestion Script
===========================================================
Ingests database schema into the RAG knowledge base.

This script:
1. Extracts all table schemas
2. Generates embeddings using Google's embedding model
3. Stores them in the knowledge_documents table with pgvector

Run this after setting up the database and before using the agent.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.agent.rag_retriever import ingest_schema_knowledge, get_knowledge_stats
from backend.app.db.connection import test_connection

def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Cognitive Database Agent - Knowledge Ingestion")
    print("=" * 60)
    print()

    # Test database connection
    print("Testing database connection...")
    if not test_connection():
        print("✗ Database connection failed!")
        print("Please check your .env configuration and ensure the database is set up.")
        sys.exit(1)

    print("✓ Database connection successful")
    print()

    # Check existing knowledge
    print("Checking existing knowledge base...")
    try:
        stats = get_knowledge_stats()
        print(f"Current documents: {stats['total_documents']}")

        if stats['total_documents'] > 0:
            response = input("\nKnowledge base already has documents. Clear and re-ingest? (y/n): ")
            if response.lower() != 'y':
                print("Ingestion cancelled.")
                sys.exit(0)

            # Clear existing knowledge
            from backend.app.agent.rag_retriever import clear_knowledge_base
            print("\nClearing existing knowledge...")
            cleared = clear_knowledge_base()
            print(f"✓ Cleared {cleared} documents")
    except Exception as e:
        print(f"Warning: Could not check existing knowledge: {e}")

    print()

    # Ingest schema knowledge
    print("Starting schema ingestion...")
    print("This may take a few minutes to generate embeddings...")
    print()

    try:
        count = ingest_schema_knowledge()
        print()
        print("=" * 60)
        print(f"✓ Successfully ingested {count} documents!")
        print("=" * 60)
        print()

        # Show statistics
        stats = get_knowledge_stats()
        print("Knowledge base statistics:")
        print(f"  Total documents: {stats['total_documents']}")
        print(f"  By type:")
        for doc_type, count in stats.get('by_type', {}).items():
            print(f"    - {doc_type}: {count}")

        print()
        print("Knowledge base is ready! You can now:")
        print("  - Start the API server: python backend\\main.py")
        print("  - Try the CLI demo: python backend\\cli_demo.py")
        print()

    except Exception as e:
        print()
        print(f"✗ Ingestion failed: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Ensure your GOOGLE_API_KEY is set in .env")
        print("  2. Check that the database has the pgvector extension")
        print("  3. Verify the knowledge_documents table exists")
        sys.exit(1)


if __name__ == "__main__":
    main()
