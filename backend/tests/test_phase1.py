import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app.core.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from backend.app.agent.query_validator import QueryValidator
from backend.main import app

client = TestClient(app)

def test_password_hashing():
    password = "secure_password_123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong_password", hashed)

def test_jwt_tokens():
    token_data = {
        "sub": "test_user",
        "user_id": "12345678-1234-1234-1234-123456789012",
        "role": "admin",
        "region": "North"
    }
    token = create_access_token(token_data)
    assert token
    
    decoded = decode_access_token(token)
    assert decoded["sub"] == "test_user"
    assert decoded["role"] == "admin"
    assert decoded["region"] == "North"
    assert decoded["user_id"] == "12345678-1234-1234-1234-123456789012"
    
    # Test invalid token raises HTTPException
    with pytest.raises(HTTPException) as exc:
        decode_access_token("invalid.jwt.token")
    assert exc.value.status_code == 401

def test_sql_validator_comments():
    query_with_comments = """
    -- This is a comment
    SELECT * FROM sales_data; /* Inline comment */
    """
    clean_query = QueryValidator.strip_comments(query_with_comments)
    assert "This is a comment" not in clean_query
    assert "Inline comment" not in clean_query
    assert clean_query == "SELECT * FROM sales_data;"

def test_sql_validator_stacked():
    single_query = "SELECT * FROM sales_data"
    stacked_query = "SELECT * FROM sales_data; SELECT * FROM users;"
    
    assert not QueryValidator.has_stacked_statements(single_query)
    assert QueryValidator.has_stacked_statements(stacked_query)
    
    is_valid, reason = QueryValidator.validate(stacked_query, "SELECT")
    assert not is_valid
    assert "Stacked queries" in reason

def test_sql_validator_subquery_depth():
    valid_subquery = "SELECT * FROM (SELECT * FROM (SELECT * FROM sales_data))"
    invalid_subquery = "SELECT * FROM (SELECT * FROM (SELECT * FROM (SELECT * FROM sales_data)))"
    
    assert QueryValidator.check_subquery_depth(valid_subquery) == 2
    assert QueryValidator.check_subquery_depth(invalid_subquery) == 3
    
    too_deep = "SELECT * FROM (SELECT * FROM (SELECT * FROM (SELECT * FROM (SELECT * FROM sales_data))))"
    assert QueryValidator.check_subquery_depth(too_deep) == 4
    
    is_valid, reason = QueryValidator.validate(too_deep, "SELECT")
    assert not is_valid
    assert "Subquery nesting depth" in reason

def test_sql_validator_blocklist():
    valid_query = "SELECT alter_ego FROM users"  # alter_ego contains alter, but is valid name
    is_valid, reason = QueryValidator.validate(valid_query, "SELECT")
    assert is_valid
    
    invalid_query = "ALTER TABLE users ADD COLUMN age INT;"
    is_valid, reason = QueryValidator.validate(invalid_query, "ALTER")
    assert not is_valid
    assert "blocked keyword" in reason

def test_rate_limiting():
    # Clear rate limit history before testing
    from backend.app.agent.query_validator import _rate_limit_history
    _rate_limit_history["viewer"].clear()
    
    # Enforce rate limit 30 times should be fine
    for _ in range(30):
        QueryValidator.enforce_rate_limit("viewer")
        
    # 31st time should raise HTTP 429
    with pytest.raises(HTTPException) as exc:
        QueryValidator.enforce_rate_limit("viewer")
    assert exc.value.status_code == 429
    assert "Rate limit exceeded" in exc.value.detail

@patch("backend.app.api.routes.auth.execute_query")
def test_login_endpoint(mock_execute_query):
    # Mock user returned from database
    mock_execute_query.return_value = [{
        "id": "12345678-1234-1234-1234-123456789012",
        "username": "admin_user",
        "password_hash": hash_password("admin123"),
        "role": "db_admin",
        "region": None,
        "is_active": True
    }]
    
    response = client.post("/api/auth/login", json={
        "username": "admin_user",
        "password": "admin123"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "admin"
    assert data["region"] is None
    
    # Test invalid password login
    response_invalid = client.post("/api/auth/login", json={
        "username": "admin_user",
        "password": "wrongpassword"
    })
    assert response_invalid.status_code == 401
    assert "Incorrect username or password" in response_invalid.json()["detail"]

@patch("backend.app.api.routes.auth.execute_query")
def test_get_me_endpoint(mock_execute_query):
    # Retrieve user from mock DB
    mock_execute_query.return_value = [{
        "id": "12345678-1234-1234-1234-123456789012",
        "username": "admin_user",
        "password_hash": hash_password("admin123"),
        "role": "db_admin",
        "region": None,
        "is_active": True
    }]
    
    # First login to get a token
    login_resp = client.post("/api/auth/login", json={
        "username": "admin_user",
        "password": "admin123"
    })
    token = login_resp.json()["access_token"]
    
    # Call /api/auth/me with token
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/auth/me", headers=headers)
    
    assert response.status_code == 200
    user_info = response.json()
    assert user_info["username"] == "admin_user"
    assert user_info["role"] == "admin"
    assert user_info["region"] is None
    assert user_info["user_id"] == "12345678-1234-1234-1234-123456789012"

@patch("backend.app.api.routes.agent.session_manager.get_or_create_agent")
@patch("backend.app.api.routes.auth.execute_query")
def test_chat_endpoint_dry_run(mock_execute_query, mock_get_agent):
    # Mock login DB call
    mock_execute_query.return_value = [{
        "id": "12345678-1234-1234-1234-123456789012",
        "username": "admin_user",
        "password_hash": hash_password("admin123"),
        "role": "db_admin",
        "region": None,
        "is_active": True
    }]
    
    # Login to get token
    login_resp = client.post("/api/auth/login", json={
        "username": "admin_user",
        "password": "admin123"
    })
    token = login_resp.json()["access_token"]
    
    # Mock Agent Executor response
    mock_agent = MagicMock()
    mock_agent.run.return_value = {
        "success": True,
        "query": "SELECT * FROM sales_data",
        "response": "Dry-run mode: SELECT query generated and validated successfully.",
        "role": "admin",
        "region": None,
        "intermediate_steps": []
    }
    mock_get_agent.return_value = mock_agent
    
    # Chat with dry_run flag set to True
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/chat", json={
        "message": "Show all sales data",
        "dry_run": True
    }, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"]
    assert "SELECT * FROM sales_data" in data["query"]
    assert "admin" == data["role"]
