"""
Cognitive Database Agent - Database Connection Module
=====================================================
Provides secure database connections with role impersonation for RLS.

Key Features:
- Connection pooling
- Role impersonation via SET LOCAL ROLE
- Context managers for automatic cleanup
- Transaction support
"""

import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
import logging

from backend.app.core.config import settings, get_db_connection_params, get_role_name

# Setup logging
logger = logging.getLogger(__name__)


# ================================
# Connection Pool
# ================================
class DatabasePool:
    """
    PostgreSQL connection pool manager.
    Maintains a pool of connections for efficient database access.
    """

    def __init__(self, minconn: int = 1, maxconn: int = 10):
        """
        Initialize connection pool.

        Args:
            minconn: Minimum number of connections in pool
            maxconn: Maximum number of connections in pool
        """
        try:
            self.pool = psycopg2.pool.SimpleConnectionPool(
                minconn,
                maxconn,
                **get_db_connection_params(),
            )
            logger.info(f"Database connection pool created (min={minconn}, max={maxconn})")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise

    def get_connection(self):
        """
        Get a connection from the pool.

        Returns:
            psycopg2 connection object
        """
        try:
            conn = self.pool.getconn()
            return conn
        except Exception as e:
            logger.error(f"Failed to get connection from pool: {e}")
            raise

    def return_connection(self, conn):
        """
        Return a connection to the pool.

        Args:
            conn: Connection to return
        """
        try:
            self.pool.putconn(conn)
        except Exception as e:
            logger.error(f"Failed to return connection to pool: {e}")
            raise

    def close_all(self):
        """Close all connections in the pool."""
        try:
            self.pool.closeall()
            logger.info("All database connections closed")
        except Exception as e:
            logger.error(f"Failed to close connections: {e}")
            raise


# Global connection pool
_db_pool: Optional[DatabasePool] = None


def get_pool() -> DatabasePool:
    """
    Get the global database connection pool.
    Creates the pool if it doesn't exist.

    Returns:
        DatabasePool instance
    """
    global _db_pool
    if _db_pool is None:
        _db_pool = DatabasePool()
    return _db_pool


# ================================
# Context Managers
# ================================
@contextmanager
def get_db_connection(role: Optional[str] = None, region: Optional[str] = None):
    """
    Context manager for database connections with optional role impersonation.

    Args:
        role: Role to impersonate ('admin', 'manager', 'viewer')
        region: Region for manager role (required if role is 'manager')

    Yields:
        psycopg2 connection object

    Example:
        >>> with get_db_connection(role='admin') as conn:
        >>>     cursor = conn.cursor()
        >>>     cursor.execute("SELECT * FROM sales_data")
        >>>     results = cursor.fetchall()
    """
    pool = get_pool()
    conn = None

    try:
        # Get connection from pool
        conn = pool.get_connection()
        conn.autocommit = False

        # Start transaction
        cursor = conn.cursor()

        # Set role if specified
        if role:
            db_role = get_role_name(role)
            logger.debug(f"Setting role to: {db_role}")

            # Set the role
            cursor.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(db_role)))

            # Set region for manager role
            if role.lower() == "manager" and region:
                logger.debug(f"Setting region to: {region}")
                cursor.execute(
                    sql.SQL("SET LOCAL app.user_region = %s"),
                    [region],
                )

        cursor.close()

        # Yield connection to caller
        yield conn

        # Commit transaction if no exceptions
        conn.commit()

    except Exception as e:
        # Rollback on error
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise

    finally:
        # Reset role and return connection to pool
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("RESET ROLE")
                cursor.close()
            except Exception as e:
                logger.error(f"Failed to reset role: {e}")

            pool.return_connection(conn)


@contextmanager
def get_db_cursor(
    role: Optional[str] = None, region: Optional[str] = None, dict_cursor: bool = True
):
    """
    Context manager for database cursors with role impersonation.

    Args:
        role: Role to impersonate ('admin', 'manager', 'viewer')
        region: Region for manager role
        dict_cursor: If True, return RealDictCursor (results as dicts)

    Yields:
        psycopg2 cursor object

    Example:
        >>> with get_db_cursor(role='viewer') as cursor:
        >>>     cursor.execute("SELECT * FROM sales_data WHERE year = 2022")
        >>>     results = cursor.fetchall()
    """
    with get_db_connection(role=role, region=region) as conn:
        cursor_class = RealDictCursor if dict_cursor else None
        cursor = conn.cursor(cursor_factory=cursor_class)
        try:
            yield cursor
        finally:
            cursor.close()


# ================================
# Helper Functions
# ================================
def execute_query(
    query: str,
    params: Optional[tuple] = None,
    role: Optional[str] = None,
    region: Optional[str] = None,
    fetch: bool = True,
) -> Optional[List[Dict[str, Any]]]:
    """
    Execute a SQL query with role impersonation.

    Args:
        query: SQL query to execute
        params: Query parameters
        role: Role to execute as ('admin', 'manager', 'viewer')
        region: Region for manager role
        fetch: If True, fetch and return results

    Returns:
        List of result dictionaries if fetch=True, None otherwise

    Example:
        >>> results = execute_query(
        >>>     "SELECT * FROM sales_data WHERE year = %s",
        >>>     params=(2022,),
        >>>     role='viewer'
        >>> )
    """
    with get_db_cursor(role=role, region=region) as cursor:
        cursor.execute(query, params or ())

        if fetch:
            results = cursor.fetchall()
            logger.debug(f"Query returned {len(results)} rows")
            return results
        else:
            logger.debug(f"Query executed, {cursor.rowcount} rows affected")
            return None


def execute_insert(
    table: str,
    data: Dict[str, Any],
    role: Optional[str] = None,
    region: Optional[str] = None,
    returning: str = "*",
) -> Optional[Dict[str, Any]]:
    """
    Insert a row into a table with role impersonation.

    Args:
        table: Table name
        data: Dictionary of column:value pairs
        role: Role to execute as
        region: Region for manager role
        returning: Columns to return (default: all)

    Returns:
        Inserted row as dictionary

    Example:
        >>> result = execute_insert(
        >>>     'sales_data',
        >>>     {'year': 2024, 'amount': 50000, 'region': 'North'},
        >>>     role='manager',
        >>>     region='North'
        >>> )
    """
    columns = list(data.keys())
    values = list(data.values())
    placeholders = ["%s"] * len(values)

    query = sql.SQL("INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING {returning}").format(
        table=sql.Identifier(table),
        columns=sql.SQL(", ").join(map(sql.Identifier, columns)),
        placeholders=sql.SQL(", ").join(map(sql.SQL, placeholders)),
        returning=sql.SQL(returning),
    )

    with get_db_cursor(role=role, region=region) as cursor:
        cursor.execute(query, values)
        result = cursor.fetchone()
        logger.debug(f"Inserted row into {table}")
        return result


def test_connection() -> bool:
    """
    Test database connection.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            logger.info("Database connection test successful")
            return result is not None
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


def close_pool():
    """Close the database connection pool."""
    global _db_pool
    if _db_pool:
        _db_pool.close_all()
        _db_pool = None


# ================================
# Export public API
# ================================
__all__ = [
    "get_db_connection",
    "get_db_cursor",
    "execute_query",
    "execute_insert",
    "test_connection",
    "close_pool",
    "DatabasePool",
    "get_pool",
]
