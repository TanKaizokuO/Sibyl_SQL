"""
Cognitive Database Agent - RAG Retrieval Module
===============================================
Implements Retrieval-Augmented Generation (RAG) for schema knowledge.

This module:
1. Generates embeddings using Google's embedding model
2. Stores embeddings in PostgreSQL with pgvector
3. Performs semantic search to retrieve relevant context
4. Provides context to the LLM agent

THEORY: Why RAG is necessary for database agents
-------------------------------------------------
- LLMs have limited context windows and don't know your specific schema
- RAG allows the agent to "understand" your database structure on-demand
- Semantic search finds relevant information even with ambiguous queries
- Example: "show sales from last year" → retrieves sales_data schema + year column info
"""

import logging
import json
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer

from backend.app.core.config import settings
from backend.app.db.connection import get_db_cursor, execute_query
from backend.app.agent.schema_extractor import extract_all_schemas, generate_example_queries

logger = logging.getLogger(__name__)


# ================================
# Embedding Model
# ================================
class EmbeddingModel:
    """
    Wrapper for local sentence-transformers embedding model.
    Handles text-to-vector conversion for RAG using free, local embeddings.

    Model: all-MiniLM-L6-v2
    - Dimension: 384
    - Fast and lightweight
    - No API keys required
    - No quota limits
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize the embedding model."""
        try:
            logger.info(f"Loading sentence-transformers model: {model_name}")
            self.model = SentenceTransformer(model_name)
            logger.info(f"✓ Initialized local embedding model: {model_name}")
            logger.info(f"  Embedding dimension: {self.model.get_sentence_embedding_dimension()}")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            raise

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding vector for text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector as list of floats
        """
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            embedding_list = embedding.tolist()
            logger.debug(f"Generated embedding (dimension: {len(embedding_list)})")
            return embedding_list
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
            embeddings_list = embeddings.tolist()
            logger.debug(f"Generated {len(embeddings_list)} embeddings")
            return embeddings_list
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise


# Global embedding model instance
_embedding_model: Optional[EmbeddingModel] = None


def get_embedding_model() -> EmbeddingModel:
    """
    Get the global embedding model instance.

    Returns:
        EmbeddingModel instance
    """
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = EmbeddingModel()
    return _embedding_model


# ================================
# Knowledge Base Ingestion
# ================================
def ingest_schema_knowledge():
    """
    Extract all schemas and ingest them into the knowledge base with embeddings.
    This should be run once during setup or when schema changes.
    """
    logger.info("Starting schema knowledge ingestion...")

    # Get embedding model
    model = get_embedding_model()

    # Extract all schemas
    schemas = extract_all_schemas()

    # Prepare documents for ingestion
    documents_to_ingest = []

    # Add schema descriptions
    for schema in schemas:
        documents_to_ingest.append(
            {
                "content": schema["description"],
                "doc_type": "schema",
                "metadata": {"table": schema["table_name"]},
            }
        )

        # Add example queries for this table
        examples = generate_example_queries(schema["table_name"])
        for example in examples:
            documents_to_ingest.append(
                {
                    "content": f"{example['description']}\nSQL: {example['query']}",
                    "doc_type": "example_query",
                    "metadata": {"table": schema["table_name"], "query": example["query"]},
                }
            )

    logger.info(f"Prepared {len(documents_to_ingest)} documents for ingestion")

    # Generate embeddings in batch
    texts = [doc["content"] for doc in documents_to_ingest]
    try:
        embeddings = model.embed_documents(texts)
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        raise

    # Insert into database
    insert_query = """
        INSERT INTO knowledge_documents (content, embedding, doc_type, metadata)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """

    inserted_count = 0
    with get_db_cursor(dict_cursor=False) as cursor:
        for doc, embedding in zip(documents_to_ingest, embeddings):
            try:
                # Convert embedding to PostgreSQL array format
                embedding_str = "[" + ",".join(map(str, embedding)) + "]"

                cursor.execute(
                    insert_query,
                    (
                        doc["content"],
                        embedding_str,
                        doc["doc_type"],
                        json.dumps(doc["metadata"]),  # Convert dict to JSON string
                    ),
                )
                inserted_count += 1
            except Exception as e:
                logger.warning(f"Failed to insert document: {e}")

    logger.info(f"Ingested {inserted_count} documents into knowledge base")
    return inserted_count


def add_custom_knowledge(content: str, doc_type: str = "custom", metadata: Optional[Dict] = None):
    """
    Add a custom knowledge document to the RAG knowledge base.

    Args:
        content: Text content to add
        doc_type: Type of document (default: 'custom')
        metadata: Optional metadata dictionary
    """
    model = get_embedding_model()

    # Generate embedding
    embedding = model.embed_text(content)
    embedding_str = "[" + ",".join(map(str, embedding)) + "]"

    # Insert into database
    insert_query = """
        INSERT INTO knowledge_documents (content, embedding, doc_type, metadata)
        VALUES (%s, %s, %s, %s)
    """

    with get_db_cursor(dict_cursor=False) as cursor:
        cursor.execute(
            insert_query,
            (content, embedding_str, doc_type, json.dumps(metadata or {})),
        )

    logger.info(f"Added custom knowledge document (type: {doc_type})")


# ================================
# Semantic Search / Retrieval
# ================================
def retrieve_relevant_context(
    query: str,
    top_k: int = None,
    doc_type_filter: Optional[str] = None,
    similarity_threshold: float = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve relevant context from knowledge base using semantic search.

    Args:
        query: User's query text
        top_k: Number of results to return (default: from settings)
        doc_type_filter: Filter by document type (e.g., 'schema', 'example_query')
        similarity_threshold: Minimum similarity score (default: from settings)

    Returns:
        List of relevant documents with similarity scores

    Example:
        >>> results = retrieve_relevant_context("show sales from 2022")
        >>> # Returns schema for sales_data table + example queries
    """
    if top_k is None:
        top_k = settings.rag_top_k
    if similarity_threshold is None:
        similarity_threshold = settings.rag_similarity_threshold

    # Generate query embedding
    model = get_embedding_model()
    query_embedding = model.embed_text(query)
    query_embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

    # Build SQL query with pgvector cosine similarity
    sql_query = """
        SELECT
            id,
            content,
            doc_type,
            metadata,
            1 - (embedding <=> %s::vector) AS similarity
        FROM knowledge_documents
        WHERE 1 = 1
    """

    params = [query_embedding_str]

    # Add type filter if specified
    if doc_type_filter:
        sql_query += " AND doc_type = %s"
        params.append(doc_type_filter)

    # Add similarity threshold
    sql_query += " AND (1 - (embedding <=> %s::vector)) >= %s"
    params.extend([query_embedding_str, similarity_threshold])

    # Order by similarity and limit
    sql_query += " ORDER BY similarity DESC LIMIT %s"
    params.append(top_k)

    # Execute query
    with get_db_cursor() as cursor:
        cursor.execute(sql_query, params)
        results = cursor.fetchall()

    logger.info(f"Retrieved {len(results)} relevant documents for query: '{query[:50]}...'")

    return results


def format_context_for_agent(retrieved_docs: List[Dict[str, Any]]) -> str:
    """
    Format retrieved documents into a context string for the agent.

    Args:
        retrieved_docs: List of retrieved documents from retrieve_relevant_context

    Returns:
        Formatted context string
    """
    if not retrieved_docs:
        return "No relevant schema information found."

    context_parts = ["=== RELEVANT DATABASE SCHEMA AND EXAMPLES ===\n"]

    for i, doc in enumerate(retrieved_docs, 1):
        context_parts.append(f"\n[Document {i}] (Similarity: {doc['similarity']:.2f})")
        context_parts.append(f"Type: {doc['doc_type']}")
        context_parts.append(f"Content:\n{doc['content']}")

        if doc["metadata"]:
            context_parts.append(f"Metadata: {doc['metadata']}")

        context_parts.append("-" * 60)

    return "\n".join(context_parts)


def get_context_for_query(query: str, include_examples: bool = True) -> str:
    """
    High-level function to get formatted context for a user query.

    Args:
        query: User's natural language query
        include_examples: Whether to include example queries

    Returns:
        Formatted context string ready for the agent
    """
    # Retrieve schema information
    schema_docs = retrieve_relevant_context(
        query,
        top_k=3,
        doc_type_filter="schema",
    )

    # Retrieve example queries if requested
    example_docs = []
    if include_examples:
        example_docs = retrieve_relevant_context(
            query,
            top_k=2,
            doc_type_filter="example_query",
        )

    # Combine all documents
    all_docs = schema_docs + example_docs

    # Format and return
    return format_context_for_agent(all_docs)


def clear_knowledge_base():
    """
    Clear all documents from the knowledge base.
    Use with caution!
    """
    with get_db_cursor(dict_cursor=False) as cursor:
        cursor.execute("DELETE FROM knowledge_documents")
        deleted_count = cursor.rowcount

    logger.warning(f"Cleared {deleted_count} documents from knowledge base")
    return deleted_count


def get_knowledge_stats() -> Dict[str, Any]:
    """
    Get statistics about the knowledge base.

    Returns:
        Dictionary with stats
    """
    stats_query = """
        SELECT
            doc_type,
            COUNT(*) as count
        FROM knowledge_documents
        GROUP BY doc_type
    """

    with get_db_cursor() as cursor:
        cursor.execute(stats_query)
        results = cursor.fetchall()

        # Get total count
        cursor.execute("SELECT COUNT(*) as total FROM knowledge_documents")
        total_result = cursor.fetchone()

    stats = {
        "total_documents": total_result["total"] if total_result else 0,
        "by_type": {row["doc_type"]: row["count"] for row in results},
    }

    logger.info(f"Knowledge base stats: {stats}")
    return stats


# ================================
# Export public API
# ================================
__all__ = [
    "EmbeddingModel",
    "get_embedding_model",
    "ingest_schema_knowledge",
    "add_custom_knowledge",
    "retrieve_relevant_context",
    "get_context_for_query",
    "format_context_for_agent",
    "clear_knowledge_base",
    "get_knowledge_stats",
]
