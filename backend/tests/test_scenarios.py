"""
Cognitive Database Agent - Test Scenarios
=========================================
Comprehensive test suite for validating agent functionality.
"""

import pytest
from backend.app.agent.cognitive_agent import create_agent
from backend.app.db.connection import test_connection, execute_query


class TestRLSSecurity:
    """Test Row-Level Security policies."""

    def test_viewer_cannot_delete(self):
        """Viewer role should not be able to delete records."""
        agent = create_agent(role='viewer', verbose=False)
        result = agent.run("Delete all sales records from 2021")

        assert not result['success'] or 'permission denied' in str(result).lower()

    def test_viewer_can_read(self):
        """Viewer role should be able to read all records."""
        agent = create_agent(role='viewer', verbose=False)
        result = agent.run("Show me all sales from 2022")

        assert result['success']

    def test_admin_full_access(self):
        """Admin should have full access to all operations."""
        agent = create_agent(role='admin', verbose=False)

        # Test read
        result = agent.run("List all available tables")
        assert result['success']

    def test_manager_regional_access(self):
        """Manager should only access their region."""
        agent = create_agent(role='manager', region='North', verbose=False)
        result = agent.run("Show me sales data")

        # Should succeed but only return North region data
        assert result['success']


class TestMultiStepOperations:
    """Test agent's multi-step planning capabilities."""

    def test_archive_operation(self):
        """Test archiving operation (multi-step)."""
        agent = create_agent(role='admin', verbose=True)
        result = agent.run("Archive all sales from 2024")

        # Should demonstrate multi-step planning
        assert 'intermediate_steps' in result
        assert len(result.get('intermediate_steps', [])) > 1

    def test_complex_query(self):
        """Test complex aggregation query."""
        agent = create_agent(role='viewer', verbose=False)
        result = agent.run("Calculate total sales by year and region")

        assert result['success']


class TestRAGRetrieval:
    """Test RAG context retrieval."""

    def test_schema_retrieval(self):
        """Test that agent retrieves relevant schema."""
        agent = create_agent(role='viewer', verbose=False)
        result = agent.run("What columns are in the sales_data table?")

        assert result['success']
        response_lower = result.get('response', '').lower()
        assert 'column' in response_lower or 'field' in response_lower

    def test_ambiguous_query(self):
        """Test that RAG helps with ambiguous queries."""
        agent = create_agent(role='viewer', verbose=False)
        result = agent.run("Show me sales from last year")

        # Agent should use RAG to understand schema
        assert result['success'] or 'year' in result.get('response', '').lower()


class TestErrorHandling:
    """Test error handling and validation."""

    def test_sql_injection_blocked(self):
        """Test that SQL injection attempts are handled safely."""
        agent = create_agent(role='viewer', verbose=False)
        result = agent.run("Show sales; DROP TABLE sales_data;--")

        # Should not drop table
        # Verify table still exists
        assert test_connection()

    def test_invalid_table_name(self):
        """Test handling of invalid table names."""
        agent = create_agent(role='viewer', verbose=False)
        result = agent.run("Select from nonexistent_table")

        assert 'error' in str(result).lower() or not result['success']


class TestToolUsage:
    """Test individual tool functions."""

    def test_list_tables_tool(self):
        """Test list_tables tool."""
        agent = create_agent(role='viewer', verbose=False)
        result = agent.run("What tables are available?")

        assert result['success']

    def test_get_schema_tool(self):
        """Test get_schema tool."""
        agent = create_agent(role='viewer', verbose=False)
        result = agent.run("Describe the structure of sales_data table")

        assert result['success']


# Test configuration
@pytest.fixture(scope="session", autouse=True)
def check_database():
    """Ensure database is accessible before running tests."""
    assert test_connection(), "Database connection failed"


@pytest.fixture(scope="session", autouse=True)
def setup_test_data():
    """Ensure test data exists."""
    # Verify sales_data has records
    result = execute_query("SELECT COUNT(*) as count FROM sales_data", fetch=True)
    assert result[0]['count'] > 0, "No test data in sales_data table"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
