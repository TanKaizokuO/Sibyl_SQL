"""
Cognitive Database Agent - Query Audit Logging Module
======================================================
Provides functions to write audit logs to the database and retrieve them for administration.
All inserts are done using the default connection pool user to avoid RLS restrictions.
"""

import logging
from typing import List, Dict, Any, Optional
from backend.app.db.connection import execute_query

logger = logging.getLogger(__name__)

def log_query(
    user_id: Optional[str],
    role: str,
    region: Optional[str],
    action: str,
    tool_name: str,
    sql_query: str,
    row_count: int,
    success: bool,
    error_message: Optional[str],
    execution_time_ms: int
) -> bool:
    """
    Log query execution details to the audit_log database table.
    Runs as the default pool user to ensure write permissions are available.
    """
    query = """
        INSERT INTO audit_log (
            user_id, role, region, action, tool_name, 
            sql_query, row_count, success, error_message, execution_time_ms
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """
    
    # Standardize UUID format for user_id
    db_user_id = None
    if user_id:
        try:
            import uuid
            db_user_id = uuid.UUID(user_id)
        except ValueError:
            logger.warning(f"Invalid UUID for user_id: {user_id}")
            db_user_id = None
            
    params = (
        db_user_id,
        role,
        region,
        action,
        tool_name,
        sql_query,
        row_count,
        success,
        error_message,
        execution_time_ms
    )
    
    try:
        # Run without role context (role=None) so the pool's admin user writes the log
        execute_query(query, params, role=None, fetch=False)
        return True
    except Exception as e:
        logger.error(f"Failed to write to audit log: {e}")
        return False


def get_audit_log(
    limit: int = 50,
    role_filter: Optional[str] = None,
    action_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve recent query audit logs.
    """
    query = """
        SELECT 
            id, user_id, role, region, action, tool_name, 
            sql_query, row_count, success, error_message, execution_time_ms, created_at 
        FROM audit_log
    """
    conditions = []
    params = []
    
    if role_filter:
        conditions.append("role = %s")
        params.append(role_filter)
        
    if action_filter:
        conditions.append("action = %s")
        params.append(action_filter.upper())
        
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
        
    query += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)
    
    try:
        results = execute_query(query, tuple(params), role=None, fetch=True)
        return results if results else []
    except Exception as e:
        logger.error(f"Failed to read from audit log: {e}")
        return []
