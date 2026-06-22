"""
Cognitive Database Agent - Schema Extraction Module
===================================================
Extracts database schema information and formats it as natural language
descriptions for the RAG knowledge base.

This module queries PostgreSQL's information_schema to get:
- Table structures
- Column details (types, constraints, defaults)
- Relationships (foreign keys)
- Indexes
- Comments
"""

import logging
from typing import List, Dict, Any, Optional
from backend.app.db.connection import get_db_cursor

logger = logging.getLogger(__name__)


# ================================
# Schema Extraction Functions
# ================================
def get_all_tables() -> List[str]:
    """
    Get list of all user tables in the database.

    Returns:
        List of table names
    """
    query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """

    with get_db_cursor() as cursor:
        cursor.execute(query)
        results = cursor.fetchall()
        tables = [row["table_name"] for row in results]
        logger.info(f"Found {len(tables)} tables: {tables}")
        return tables


def get_table_schema(table_name: str) -> Dict[str, Any]:
    """
    Get detailed schema information for a specific table.

    Args:
        table_name: Name of the table

    Returns:
        Dictionary with schema details
    """
    # Get column information
    columns_query = """
        SELECT
            column_name,
            data_type,
            character_maximum_length,
            numeric_precision,
            numeric_scale,
            is_nullable,
            column_default,
            udt_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        ORDER BY ordinal_position
    """

    # Get primary key information
    pk_query = """
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_schema = 'public'
          AND tc.table_name = %s
    """

    # Get foreign key information
    fk_query = """
        SELECT
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
          AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = 'public'
          AND tc.table_name = %s
    """

    # Get table comment
    comment_query = """
        SELECT obj_description(oid) AS comment
        FROM pg_class
        WHERE relname = %s
          AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
    """

    with get_db_cursor() as cursor:
        # Get columns
        cursor.execute(columns_query, (table_name,))
        columns = cursor.fetchall()

        # Get primary key
        cursor.execute(pk_query, (table_name,))
        pk_results = cursor.fetchall()
        primary_keys = [row["column_name"] for row in pk_results]

        # Get foreign keys
        cursor.execute(fk_query, (table_name,))
        foreign_keys = cursor.fetchall()

        # Get table comment
        cursor.execute(comment_query, (table_name,))
        comment_result = cursor.fetchone()
        table_comment = comment_result["comment"] if comment_result and comment_result["comment"] else ""

    return {
        "table_name": table_name,
        "columns": columns,
        "primary_keys": primary_keys,
        "foreign_keys": foreign_keys,
        "comment": table_comment,
    }


def format_column_description(column: Dict[str, Any], is_pk: bool = False, fk_info: Optional[Dict] = None) -> str:
    """
    Format a column description in natural language.

    Args:
        column: Column information dictionary
        is_pk: Whether this column is a primary key
        fk_info: Foreign key information if applicable

    Returns:
        Natural language description
    """
    name = column["column_name"]
    dtype = column["data_type"]
    nullable = "optional" if column["is_nullable"] == "YES" else "required"
    default = f" with default value {column['column_default']}" if column["column_default"] else ""

    description = f"{name} ({dtype}, {nullable}{default})"

    if is_pk:
        description += " [PRIMARY KEY]"

    if fk_info:
        description += f" [FOREIGN KEY -> {fk_info['foreign_table_name']}.{fk_info['foreign_column_name']}]"

    return description


def schema_to_natural_language(table_name: str) -> str:
    """
    Convert table schema to natural language description.

    Args:
        table_name: Name of the table

    Returns:
        Natural language description of the schema
    """
    schema = get_table_schema(table_name)

    # Start with table description
    description_parts = [f"Table: {table_name}"]

    if schema["comment"]:
        description_parts.append(f"Description: {schema['comment']}")

    description_parts.append("\nColumns:")

    # Create foreign key lookup
    fk_lookup = {fk["column_name"]: fk for fk in schema["foreign_keys"]}

    # Format each column
    for column in schema["columns"]:
        col_name = column["column_name"]
        is_pk = col_name in schema["primary_keys"]
        fk_info = fk_lookup.get(col_name)

        col_desc = format_column_description(column, is_pk, fk_info)
        description_parts.append(f"  - {col_desc}")

    # Add relationships summary
    if schema["foreign_keys"]:
        description_parts.append("\nRelationships:")
        for fk in schema["foreign_keys"]:
            description_parts.append(
                f"  - {fk['column_name']} references {fk['foreign_table_name']}.{fk['foreign_column_name']}"
            )

    return "\n".join(description_parts)


def extract_all_schemas() -> List[Dict[str, Any]]:
    """
    Extract schema information for all tables.

    Returns:
        List of dictionaries with table name and natural language description
    """
    tables = get_all_tables()
    schemas = []

    for table in tables:
        try:
            nl_description = schema_to_natural_language(table)
            schemas.append(
                {
                    "table_name": table,
                    "description": nl_description,
                    "type": "schema",
                }
            )
            logger.info(f"Extracted schema for table: {table}")
        except Exception as e:
            logger.error(f"Failed to extract schema for {table}: {e}")

    return schemas


def generate_example_queries(table_name: str) -> List[Dict[str, Any]]:
    """
    Generate example queries for a table based on its schema.

    Args:
        table_name: Name of the table

    Returns:
        List of example queries with descriptions
    """
    schema = get_table_schema(table_name)
    examples = []

    # Basic SELECT all
    examples.append(
        {
            "query": f"SELECT * FROM {table_name}",
            "description": f"Retrieve all records from {table_name}",
            "type": "example_query",
        }
    )

    # Find common column types for examples
    date_cols = [c["column_name"] for c in schema["columns"] if "date" in c["data_type"].lower() or "timestamp" in c["data_type"].lower()]
    numeric_cols = [c["column_name"] for c in schema["columns"] if c["data_type"] in ("integer", "numeric", "decimal", "real", "double precision")]
    text_cols = [c["column_name"] for c in schema["columns"] if c["data_type"] in ("character varying", "text", "varchar")]

    # Add aggregate example if numeric columns exist
    if numeric_cols:
        col = numeric_cols[0]
        examples.append(
            {
                "query": f"SELECT SUM({col}) FROM {table_name}",
                "description": f"Calculate total {col} from {table_name}",
                "type": "example_query",
            }
        )

    # Add filtering example if text columns exist
    if text_cols:
        col = text_cols[0]
        examples.append(
            {
                "query": f"SELECT * FROM {table_name} WHERE {col} = '<value>'",
                "description": f"Filter {table_name} by {col}",
                "type": "example_query",
            }
        )

    return examples


def get_schema_summary() -> str:
    """
    Get a high-level summary of the entire database schema.

    Returns:
        Natural language summary
    """
    tables = get_all_tables()

    summary_parts = [
        "Database Schema Summary",
        f"Total tables: {len(tables)}",
        "\nTables:",
    ]

    for table in tables:
        schema = get_table_schema(table)
        col_count = len(schema["columns"])
        summary_parts.append(f"  - {table} ({col_count} columns)")

    return "\n".join(summary_parts)


# ================================
# Export public API
# ================================
__all__ = [
    "get_all_tables",
    "get_table_schema",
    "schema_to_natural_language",
    "extract_all_schemas",
    "generate_example_queries",
    "get_schema_summary",
]
