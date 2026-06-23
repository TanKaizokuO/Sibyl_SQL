"""
Cognitive Database Agent - Custom LangChain Tools
=================================================
Defines custom tools that the agent can use to interact with the database.

Each tool implements:
1. Role-based access control via SET LOCAL ROLE
2. Proper error handling and reporting
3. Clear descriptions for the LLM to understand when to use them

Available Tools:
- list_tables_tool: Get list of available tables
- get_schema_tool: Get detailed schema for a specific table
- run_secure_query_tool: Execute SELECT queries with role context
- run_secure_insert_tool: Execute INSERT with role context
- run_secure_update_tool: Execute UPDATE with role context
- run_secure_delete_tool: Execute DELETE with role context
"""

import logging
import json
import time
from typing import Optional, Dict, Any
from contextvars import ContextVar
from langchain_core.tools import Tool
from pydantic import BaseModel, Field

from backend.app.db.connection import get_db_cursor, execute_query
from backend.app.agent.schema_extractor import get_all_tables, schema_to_natural_language
from backend.app.core.auth import current_user_var
from backend.app.agent.query_validator import QueryValidator
from backend.app.db.audit import log_query

# Thread-safe ContextVar to flag dry-run executions.
# When True, SQL statement writes (INSERT, UPDATE, DELETE) are parsed and validated
# but not committed, allowing validation tests to run safely.
dry_run_var: ContextVar[bool] = ContextVar("dry_run", default=False)

logger = logging.getLogger(__name__)


# ================================
# Tool Input Schemas
# ================================
class QueryInput(BaseModel):
    """Input schema for query execution tools."""

    query: str = Field(description="The SQL query to execute")


class SchemaInput(BaseModel):
    """Input schema for schema retrieval tool."""

    table_name: str = Field(description="Name of the table to get schema for")


# ================================
# Shared State for Role Context
# ================================
class AgentContext:
    """
    Shared context for agent execution.
    Stores the current role and region for all tool calls.

    This context is dynamically set by the ReAct agent framework at the beginning
    of the query loop, ensuring that all subsequent SQL tools impersonate the
    correct DB role (e.g., db_viewer, db_manager, db_admin) and enforce proper RLS.
    """

    def __init__(self, role: str = "viewer", region: Optional[str] = None):
        self.role = role
        self.region = region

    def __repr__(self):
        return f"AgentContext(role={self.role}, region={self.region})"


# Global context (will be set by agent)
_current_context: Optional[AgentContext] = None


def set_agent_context(role: str, region: Optional[str] = None):
    """
    Set the current agent context for all tool executions.

    Args:
        role: Database role to use ('admin', 'manager', 'viewer')
        region: Region for manager role
    """
    global _current_context
    _current_context = AgentContext(role=role, region=region)
    logger.info(f"Agent context set: {_current_context}")


def get_agent_context() -> AgentContext:
    """
    Get the current agent context.

    Returns:
        AgentContext instance
    """
    if _current_context is None:
        logger.warning("No agent context set, using default (viewer)")
        return AgentContext(role="viewer")
    return _current_context


# ================================
# Tool Functions
# ================================
def list_tables_func(input: str = "") -> str:
    """
    List all available tables in the database.

    Args:
        input: Ignored (required by LangChain tool interface)

    Returns:
        JSON string with list of tables
    """
    try:
        tables = get_all_tables()
        result = {
            "success": True,
            "tables": tables,
            "count": len(tables),
        }
        logger.info(f"Listed {len(tables)} tables")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Failed to list tables: {e}")
        return json.dumps({"success": False, "error": str(e)})


def get_schema_func(table_name: str) -> str:
    """
    Get detailed schema information for a specific table.

    Args:
        table_name: Name of the table

    Returns:
        JSON string with schema details
    """
    # Sanitize input - strip any extra text, punctuation, or enclosing quotes/backticks the LLM might add
    # Example: "'sales_data' (assuming this is...)" -> "sales_data"
    cleaned = table_name.split('(')[0].split()[0].strip()
    table_name = cleaned.strip("'\"`;,")

    try:
        schema_desc = schema_to_natural_language(table_name)
        result = {
            "success": True,
            "table_name": table_name,
            "schema": schema_desc,
        }
        logger.info(f"Retrieved schema for table: {table_name}")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Failed to get schema for {table_name}: {e}")
        return json.dumps({"success": False, "error": str(e)})


def run_secure_query_func(query: str) -> str:
    """
    Execute a SELECT query with the current role context.

    Args:
        query: SQL SELECT query to execute

    Returns:
        JSON string with query results or error
    """
    user_context = current_user_var.get()
    role = user_context.get("role") if user_context else get_agent_context().role
    user_id = user_context.get("user_id") if user_context else None
    region = user_context.get("region") if user_context else get_agent_context().region

    # 1. Enforce rate limit
    try:
        QueryValidator.enforce_rate_limit(role)
    except HTTPException as e:
        return json.dumps({"success": False, "error": e.detail})

    # 2. Validate query
    is_valid, reason = QueryValidator.validate(query, "SELECT")
    if not is_valid:
        log_query(
            user_id=user_id,
            role=role,
            region=region,
            action="SELECT",
            tool_name="run_query",
            sql_query=query,
            row_count=0,
            success=False,
            error_message=f"Validation failed: {reason}",
            execution_time_ms=0
        )
        return json.dumps({"success": False, "error": f"Validation failed: {reason}"})

    # 3. Handle dry run
    if dry_run_var.get():
        log_query(
            user_id=user_id,
            role=role,
            region=region,
            action="SELECT",
            tool_name="run_query",
            sql_query=query,
            row_count=0,
            success=True,
            error_message="Dry run (not executed)",
            execution_time_ms=0
        )
        return json.dumps({
            "success": True,
            "query": query,
            "dry_run": True,
            "message": "Dry-run mode: SELECT query generated and validated successfully.",
            "executed_as_role": role,
            "row_count": 0,
            "data": []
        }, indent=2)

    # 4. Execute query with timing and logging
    start_time = time.time()
    success = False
    error_msg = None
    row_count = 0
    results = None

    try:
        logger.info(f"Executing query as {role}: {query[:100]}...")

        # Execute query with role context
        results = execute_query(
            query,
            role=role,
            region=region,
            fetch=True,
        )
        success = True
        row_count = len(results) if results else 0

        result = {
            "success": True,
            "query": query,
            "executed_as_role": role,
            "row_count": row_count,
            "data": results if results else [],
        }

        logger.info(f"Query returned {row_count} rows")
        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Query execution failed: {error_msg}")
        
        # Check if it's a permission error
        if "permission denied" in error_msg.lower() or "policy" in error_msg.lower():
            error_msg = f"Access denied: Your role ({role}) does not have permission to query this data. This is enforced by Row-Level Security policies. Do NOT retry the query or attempt other debugging queries. Stop and report this limitation to the user."

        return json.dumps(
            {
                "success": False,
                "error": error_msg,
                "query": query,
                "executed_as_role": role,
            }
        )
    finally:
        execution_time_ms = int((time.time() - start_time) * 1000)
        log_query(
            user_id=user_id,
            role=role,
            region=region,
            action="SELECT",
            tool_name="run_query",
            sql_query=query,
            row_count=row_count,
            success=success,
            error_message=error_msg,
            execution_time_ms=execution_time_ms
        )


def run_secure_insert_func(query: str) -> str:
    """
    Execute an INSERT query with the current role context.

    Args:
        query: SQL INSERT query to execute

    Returns:
        JSON string with result or error
    """
    user_context = current_user_var.get()
    role = user_context.get("role") if user_context else get_agent_context().role
    user_id = user_context.get("user_id") if user_context else None
    region = user_context.get("region") if user_context else get_agent_context().region

    # 1. Enforce rate limit
    try:
        QueryValidator.enforce_rate_limit(role)
    except HTTPException as e:
        return json.dumps({"success": False, "error": e.detail})

    # 2. Validate query
    is_valid, reason = QueryValidator.validate(query, "INSERT")
    if not is_valid:
        log_query(
            user_id=user_id,
            role=role,
            region=region,
            action="INSERT",
            tool_name="run_insert",
            sql_query=query,
            row_count=0,
            success=False,
            error_message=f"Validation failed: {reason}",
            execution_time_ms=0
        )
        return json.dumps({"success": False, "error": f"Validation failed: {reason}"})

    # 3. Handle dry run
    if dry_run_var.get():
        log_query(
            user_id=user_id,
            role=role,
            region=region,
            action="INSERT",
            tool_name="run_insert",
            sql_query=query,
            row_count=0,
            success=True,
            error_message="Dry run (not executed)",
            execution_time_ms=0
        )
        return json.dumps({
            "success": True,
            "query": query,
            "dry_run": True,
            "message": "Dry-run mode: INSERT query generated and validated successfully.",
            "executed_as_role": role,
            "returned_data": None
        }, indent=2)

    # 4. Execute query with timing and logging
    start_time = time.time()
    success = False
    error_msg = None
    row_count = 0
    results = None

    try:
        logger.info(f"Executing INSERT as {role}: {query[:100]}...")

        # Execute with role context
        results = execute_query(
            query,
            role=role,
            region=region,
            fetch=True,  # Fetch RETURNING clause if present
        )
        success = True
        row_count = len(results) if results else 1  # Standard single insert defaults to 1 row affected

        result = {
            "success": True,
            "query": query,
            "executed_as_role": role,
            "message": "Insert executed successfully",
            "returned_data": results if results else None,
        }

        logger.info(f"INSERT executed successfully")
        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        error_msg = str(e)
        logger.error(f"INSERT execution failed: {error_msg}")

        # Check if it's a permission error
        if "permission denied" in error_msg.lower() or "policy" in error_msg.lower():
            error_msg = f"Access denied: Your role ({role}) does not have permission to insert this data. This may be due to Row-Level Security policies."

        return json.dumps(
            {
                "success": False,
                "error": error_msg,
                "query": query,
                "executed_as_role": role,
            }
        )
    finally:
        execution_time_ms = int((time.time() - start_time) * 1000)
        log_query(
            user_id=user_id,
            role=role,
            region=region,
            action="INSERT",
            tool_name="run_insert",
            sql_query=query,
            row_count=row_count,
            success=success,
            error_message=error_msg,
            execution_time_ms=execution_time_ms
        )


def run_secure_update_func(query: str) -> str:
    """
    Execute an UPDATE query with the current role context.

    Args:
        query: SQL UPDATE query to execute

    Returns:
        JSON string with result or error
    """
    user_context = current_user_var.get()
    role = user_context.get("role") if user_context else get_agent_context().role
    user_id = user_context.get("user_id") if user_context else None
    region = user_context.get("region") if user_context else get_agent_context().region

    # 1. Enforce rate limit
    try:
        QueryValidator.enforce_rate_limit(role)
    except HTTPException as e:
        return json.dumps({"success": False, "error": e.detail})

    # 2. Validate query
    is_valid, reason = QueryValidator.validate(query, "UPDATE")
    if not is_valid:
        log_query(
            user_id=user_id,
            role=role,
            region=region,
            action="UPDATE",
            tool_name="run_update",
            sql_query=query,
            row_count=0,
            success=False,
            error_message=f"Validation failed: {reason}",
            execution_time_ms=0
        )
        return json.dumps({"success": False, "error": f"Validation failed: {reason}"})

    # 3. Handle dry run
    if dry_run_var.get():
        log_query(
            user_id=user_id,
            role=role,
            region=region,
            action="UPDATE",
            tool_name="run_update",
            sql_query=query,
            row_count=0,
            success=True,
            error_message="Dry run (not executed)",
            execution_time_ms=0
        )
        return json.dumps({
            "success": True,
            "query": query,
            "dry_run": True,
            "message": "Dry-run mode: UPDATE query generated and validated successfully.",
            "executed_as_role": role,
            "rows_affected": 0
        }, indent=2)

    # 4. Execute query with timing and logging
    start_time = time.time()
    success = False
    error_msg = None
    rows_affected = 0

    try:
        logger.info(f"Executing UPDATE as {role}: {query[:100]}...")

        # Execute with role context
        with get_db_cursor(role=role, region=region) as cursor:
            cursor.execute(query)
            rows_affected = cursor.rowcount
        success = True

        result = {
            "success": True,
            "query": query,
            "executed_as_role": role,
            "rows_affected": rows_affected,
            "message": f"Updated {rows_affected} row(s)",
        }

        logger.info(f"UPDATE affected {rows_affected} rows")
        return json.dumps(result, indent=2)

    except Exception as e:
        error_msg = str(e)
        logger.error(f"UPDATE execution failed: {error_msg}")

        # Check if it's a permission error
        if "permission denied" in error_msg.lower() or "policy" in error_msg.lower():
            error_msg = f"Access denied: Your role ({role}) does not have permission to update this data. This may be due to Row-Level Security policies."

        return json.dumps(
            {
                "success": False,
                "error": error_msg,
                "query": query,
                "executed_as_role": role,
            }
        )
    finally:
        execution_time_ms = int((time.time() - start_time) * 1000)
        log_query(
            user_id=user_id,
            role=role,
            region=region,
            action="UPDATE",
            tool_name="run_update",
            sql_query=query,
            row_count=rows_affected,
            success=success,
            error_message=error_msg,
            execution_time_ms=execution_time_ms
        )


def run_secure_delete_func(query: str) -> str:
    """
    Execute a DELETE query with the current role context.

    Args:
        query: SQL DELETE query to execute

    Returns:
        JSON string with result or error
    """
    user_context = current_user_var.get()
    role = user_context.get("role") if user_context else get_agent_context().role
    user_id = user_context.get("user_id") if user_context else None
    region = user_context.get("region") if user_context else get_agent_context().region

    # 1. Enforce rate limit
    try:
        QueryValidator.enforce_rate_limit(role)
    except HTTPException as e:
        return json.dumps({"success": False, "error": e.detail})

    # 2. Validate query
    is_valid, reason = QueryValidator.validate(query, "DELETE")
    if not is_valid:
        log_query(
            user_id=user_id,
            role=role,
            region=region,
            action="DELETE",
            tool_name="run_delete",
            sql_query=query,
            row_count=0,
            success=False,
            error_message=f"Validation failed: {reason}",
            execution_time_ms=0
        )
        return json.dumps({"success": False, "error": f"Validation failed: {reason}"})

    # 3. Handle dry run
    if dry_run_var.get():
        log_query(
            user_id=user_id,
            role=role,
            region=region,
            action="DELETE",
            tool_name="run_delete",
            sql_query=query,
            row_count=0,
            success=True,
            error_message="Dry run (not executed)",
            execution_time_ms=0
        )
        return json.dumps({
            "success": True,
            "query": query,
            "dry_run": True,
            "message": "Dry-run mode: DELETE query generated and validated successfully.",
            "executed_as_role": role,
            "rows_affected": 0
        }, indent=2)

    # 4. Execute query with timing and logging
    start_time = time.time()
    success = False
    error_msg = None
    rows_affected = 0

    try:
        logger.info(f"Executing DELETE as {role}: {query[:100]}...")

        # Execute with role context
        with get_db_cursor(role=role, region=region) as cursor:
            cursor.execute(query)
            rows_affected = cursor.rowcount
        success = True

        result = {
            "success": True,
            "query": query,
            "executed_as_role": role,
            "rows_affected": rows_affected,
            "message": f"Deleted {rows_affected} row(s)",
        }

        logger.info(f"DELETE affected {rows_affected} rows")
        return json.dumps(result, indent=2)

    except Exception as e:
        error_msg = str(e)
        logger.error(f"DELETE execution failed: {error_msg}")

        # Check if it's a permission error
        if "permission denied" in error_msg.lower() or "policy" in error_msg.lower():
            error_msg = f"Access denied: Your role ({role}) does not have permission to delete this data. This may be due to Row-Level Security policies."

        return json.dumps(
            {
                "success": False,
                "error": error_msg,
                "query": query,
                "executed_as_role": role,
            }
        )
    finally:
        execution_time_ms = int((time.time() - start_time) * 1000)
        log_query(
            user_id=user_id,
            role=role,
            region=region,
            action="DELETE",
            tool_name="run_delete",
            sql_query=query,
            row_count=rows_affected,
            success=success,
            error_message=error_msg,
            execution_time_ms=execution_time_ms
        )


# ================================
# Tool Definitions
# ================================
list_tables_tool = Tool(
    name="list_tables",
    func=list_tables_func,
    description=(
        "Lists all available tables in the database. "
        "Use this tool when you need to know what tables exist. "
        "Returns: JSON with table names."
    ),
)

get_schema_tool = Tool(
    name="get_schema",
    func=get_schema_func,
    description=(
        "Gets detailed schema information for a specific table. "
        "Input: table name (string). "
        "Returns: JSON with column names, types, constraints, and relationships. "
        "Use this before writing queries to understand table structure."
    ),
)

run_query_tool = Tool(
    name="run_query",
    func=run_secure_query_func,
    description=(
        "Executes a SELECT query on the database with role-based access control. "
        "Input: SQL SELECT query (string). "
        "Returns: JSON with query results or error message. "
        "IMPORTANT: The query will be executed with the current user's role permissions. "
        "Row-Level Security policies will automatically filter results based on role. "
        "Only SELECT statements are allowed - use specific tools for INSERT/UPDATE/DELETE."
    ),
)

run_insert_tool = Tool(
    name="run_insert",
    func=run_secure_insert_func,
    description=(
        "Executes an INSERT query with role-based access control. "
        "Input: SQL INSERT query (string). "
        "Returns: JSON with success status or error. "
        "IMPORTANT: Row-Level Security policies may block inserts based on user role and data values. "
        "For example, managers can only insert data for their assigned region."
    ),
)

run_update_tool = Tool(
    name="run_update",
    func=run_secure_update_func,
    description=(
        "Executes an UPDATE query with role-based access control. "
        "Input: SQL UPDATE query (string). "
        "Returns: JSON with number of rows affected or error. "
        "IMPORTANT: Row-Level Security policies determine which rows can be updated. "
        "You can only update rows that you have access to based on your role."
    ),
)

run_delete_tool = Tool(
    name="run_delete",
    func=run_secure_delete_func,
    description=(
        "Executes a DELETE query with role-based access control. "
        "Input: SQL DELETE query (string). "
        "Returns: JSON with number of rows deleted or error. "
        "IMPORTANT: Row-Level Security policies determine which rows can be deleted. "
        "Viewer roles typically cannot delete any rows. "
        "Managers can only delete rows in their assigned region."
    ),
)

# ================================
# Tool Collection
# ================================
def get_all_tools() -> list:
    """
    Get all available tools for the agent.

    Returns:
        List of LangChain Tool objects
    """
    return [
        list_tables_tool,
        get_schema_tool,
        run_query_tool,
        run_insert_tool,
        run_update_tool,
        run_delete_tool,
    ]


# ================================
# Export public API
# ================================
__all__ = [
    "set_agent_context",
    "get_agent_context",
    "AgentContext",
    "list_tables_tool",
    "get_schema_tool",
    "run_query_tool",
    "run_insert_tool",
    "run_update_tool",
    "run_delete_tool",
    "get_all_tools",
]
