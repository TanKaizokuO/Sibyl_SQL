"""
Cognitive Database Agent - Authentication Router
================================================
Defines API endpoints for user login and profile retrieval.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.core.auth import (create_access_token, get_current_user,
                                   verify_password)
from backend.app.db.connection import execute_query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ================================
# Request/Response Models
# ================================
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    region: Optional[str] = None


class UserProfileResponse(BaseModel):
    user_id: str
    username: str
    role: str
    region: Optional[str] = None


# ================================
# Auth Routes
# ================================
@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate user credentials against the database and generate a JWT token.
    """
    logger.info(f"Login attempt for user: {request.username}")

    try:
        # Retrieve user from auth_users table
        # We query the DB using read-only connections since we're selecting
        results = execute_query(
            "SELECT id, username, password_hash, role, region, is_active FROM auth_users WHERE username = %s",
            params=(request.username,),
            fetch=True,
        )

        if not results:
            logger.warning(f"Login failed: User {request.username} not found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = results[0]

        # Check active status
        if not user.get("is_active", True):
            logger.warning(f"Login failed: User {request.username} is deactivated")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is deactivated",
            )

        # Verify password
        if not verify_password(request.password, user["password_hash"]):
            logger.warning(
                f"Login failed: Incorrect password for user {request.username}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Map database role (db_admin, db_manager, db_viewer) to system role (admin, manager, viewer)
        db_role = user["role"]
        system_role = "viewer"
        if db_role == "db_admin":
            system_role = "admin"
        elif db_role == "db_manager":
            system_role = "manager"
        elif db_role == "db_viewer":
            system_role = "viewer"

        # Create token payload
        token_data = {
            "sub": user["username"],
            "user_id": str(user["id"]),
            "role": system_role,
            "region": user["region"],
        }

        access_token = create_access_token(token_data)

        logger.info(
            f"Successful login for user {request.username} with role {system_role}"
        )
        return LoginResponse(
            access_token=access_token, role=system_role, region=user["region"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication system error: {str(e)}",
        )


@router.get("/me", response_model=UserProfileResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Get profile information of the currently authenticated user.
    """
    return UserProfileResponse(
        user_id=current_user["user_id"],
        username=current_user["username"],
        role=current_user["role"],
        region=current_user["region"],
    )
