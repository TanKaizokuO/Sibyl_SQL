"""
Cognitive Database Agent - API Routes
=====================================
FastAPI routes for agent interaction, knowledge base management, and system status.
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from backend.app.agent.cognitive_agent import create_agent, CognitiveAgent
from backend.app.agent.session_manager import session_manager
from fastapi.responses import StreamingResponse
import asyncio
import json
from backend.app.agent.rag_retriever import (
    ingest_schema_knowledge,
    get_knowledge_stats,
    add_custom_knowledge,
    clear_knowledge_base,
)
from backend.app.agent.schema_extractor import get_all_tables, get_schema_summary
from backend.app.db.connection import test_connection
from backend.app.core.auth import get_current_user, current_user_var
from backend.app.agent.tools import dry_run_var

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api", tags=["agent"])

cleanup_task = None


@router.on_event("startup")
async def startup_cleanup_task():
    global cleanup_task
    async def periodic_cleanup():
        while True:
            try:
                await asyncio.sleep(300)  # every 5 minutes
                session_manager.cleanup_stale_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session cleanup background task: {e}")
    cleanup_task = asyncio.create_task(periodic_cleanup())


@router.on_event("shutdown")
async def shutdown_cleanup_task():
    global cleanup_task
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


# ================================
# Request/Response Models
# ================================
class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str = Field(..., description="User's message/query", min_length=1)
    conversation_id: Optional[str] = Field(default=None, description="Conversation ID for memory")
    include_rag: bool = Field(default=True, description="Include RAG context")
    dry_run: bool = Field(default=False, description="Plan query without executing")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    success: bool
    query: str
    response: Optional[str] = None
    error: Optional[str] = None
    role: str
    region: Optional[str] = None
    intermediate_steps: Optional[List] = None
    visualization_hint: Optional[Dict[str, str]] = None
    suggestions: Optional[List[Dict[str, str]]] = None


class IngestRequest(BaseModel):
    """Request model for knowledge ingestion."""

    content: str = Field(..., description="Content to add to knowledge base")
    doc_type: str = Field(default="custom", description="Type of document")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")


class RoleInfo(BaseModel):
    """Information about a database role."""

    role_name: str
    display_name: str
    description: str
    capabilities: List[str]


# ================================
# Agent Routes
# ================================
@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Send a message to the cognitive agent and get a response.

    The agent will:
    1. Retrieve relevant schema information (RAG)
    2. Plan multi-step operations if needed
    3. Execute database operations with role-based security
    4. Return results or error messages
    """
    # Set context variables for this request
    current_user_token = current_user_var.set(current_user)
    dry_run_token = dry_run_var.set(request.dry_run)

    try:
        role = current_user["role"]
        region = current_user["region"]
        
        logger.info(f"Chat request: user={current_user['username']}, role={role}, message={request.message[:100]}")

        # Validate role
        valid_roles = ["admin", "manager", "viewer"]
        if role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {valid_roles}",
            )

        # Validate region for manager role
        if role == "manager" and not region:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Region is required for manager role",
            )

        session_id = request.conversation_id or str(current_user.get("user_id")) or "default_session"

        # Get or create agent session
        agent = session_manager.get_or_create_agent(session_id, role, region)

        # Run agent
        result = agent.run(
            user_input=request.message,
            include_rag_context=request.include_rag,
        )

        logger.info(f"🔍 API DEBUG: result['intermediate_steps'] length = {len(result.get('intermediate_steps', []))}")
        logger.info(f"🔍 API DEBUG: result['intermediate_steps'] = {result.get('intermediate_steps', [])}")

        # Format response
        response = ChatResponse(
            success=result.get("success", False),
            query=result.get("query", request.message),
            response=result.get("response"),
            error=result.get("error"),
            role=result.get("role", role),
            region=result.get("region", region),
            intermediate_steps=result.get("intermediate_steps", []),
            visualization_hint=result.get("visualization_hint"),
            suggestions=result.get("suggestions", []),
        )

        logger.info(f"🔍 API DEBUG: response.intermediate_steps length = {len(response.intermediate_steps) if response.intermediate_steps else 0}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    finally:
        # Reset context variables to avoid pollution
        current_user_var.reset(current_user_token)
        dry_run_var.reset(dry_run_token)


@router.post("/chat/stream")
async def chat_with_agent_stream(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Send a message to the cognitive agent and get a streaming response (SSE).
    """
    # Set context variables for this request
    current_user_token = current_user_var.set(current_user)
    dry_run_token = dry_run_var.set(request.dry_run)

    try:
        role = current_user["role"]
        region = current_user["region"]
        session_id = request.conversation_id or str(current_user.get("user_id")) or "default_session"
        
        logger.info(f"Chat stream request: user={current_user['username']}, role={role}, session={session_id}, message={request.message[:100]}")

        # Validate role
        valid_roles = ["admin", "manager", "viewer"]
        if role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {valid_roles}",
            )

        # Validate region for manager role
        if role == "manager" and not region:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Region is required for manager role",
            )

        # Get or create agent session
        agent = session_manager.get_or_create_agent(session_id, role, region)

        async def event_generator():
            # Propagate context variables inside generator task execution
            current_user_var.set(current_user)
            dry_run_var.set(request.dry_run)
            try:
                async for event in agent.stream_run(
                    user_input=request.message,
                    include_rag_context=request.include_rag,
                ):
                    yield f"data: {json.dumps(event)}\n\n"
                
                # Signal completion
                yield "data: {\"type\": \"done\"}\n\n"
            except Exception as e:
                logger.error(f"Error in SSE generator: {e}")
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat stream endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    finally:
        current_user_var.reset(current_user_token)
        dry_run_var.reset(dry_run_token)


@router.delete("/session")
async def clear_session(
    conversation_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Clear a user's session to reset conversation memory.
    """
    session_id = conversation_id or str(current_user.get("user_id")) or "default_session"
    session_manager.destroy_session(session_id)
    return {"success": True, "message": f"Session {session_id} destroyed"}


@router.get("/roles", response_model=List[RoleInfo])
async def get_available_roles():
    """
    Get list of available database roles and their capabilities.
    """
    roles = [
        RoleInfo(
            role_name="admin",
            display_name="Administrator",
            description="Full access to all data and operations",
            capabilities=[
                "View all data across all regions",
                "Insert, update, and delete any records",
                "Access to all tables and functions",
                "No Row-Level Security restrictions",
            ],
        ),
        RoleInfo(
            role_name="manager",
            display_name="Regional Manager",
            description="Access to data in assigned region only",
            capabilities=[
                "View and modify data in assigned region",
                "Cannot access other regions' data",
                "Can insert, update, delete within region",
                "Read-only access to archived data",
            ],
        ),
        RoleInfo(
            role_name="viewer",
            display_name="Viewer",
            description="Read-only access to all data",
            capabilities=[
                "View all data across all regions",
                "Cannot insert, update, or delete any records",
                "Blocked from modifying data by RLS policies",
                "Ideal for reporting and analysis",
            ],
        ),
    ]

    return roles


# ================================
# Knowledge Base Routes
# ================================
@router.post("/ingest")
async def ingest_knowledge(current_user: dict = Depends(get_current_user)):
    """
    Ingest database schema into the RAG knowledge base.

    This extracts all table schemas, generates embeddings,
    and stores them for semantic search.
    """
    try:
        logger.info(f"User {current_user['username']} starting knowledge base ingestion")
        count = ingest_schema_knowledge()
        return {
            "success": True,
            "message": f"Successfully ingested {count} documents",
            "documents_added": count,
        }
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/ingest/custom")
async def add_custom_knowledge_document(
    request: IngestRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Add a custom document to the knowledge base.

    Useful for adding:
    - Custom business rules
    - Query examples
    - Policy descriptions
    - Domain-specific information
    """
    try:
        logger.info(f"User {current_user['username']} adding custom knowledge")
        add_custom_knowledge(
            content=request.content,
            doc_type=request.doc_type,
            metadata=request.metadata,
        )
        return {
            "success": True,
            "message": "Custom knowledge document added",
        }
    except Exception as e:
        logger.error(f"Custom ingestion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/knowledge/stats")
async def get_knowledge_base_stats():
    """
    Get statistics about the knowledge base.

    Returns counts by document type and total documents.
    """
    try:
        stats = get_knowledge_stats()
        return {
            "success": True,
            **stats,
        }
    except Exception as e:
        logger.error(f"Stats retrieval error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/knowledge")
async def clear_knowledge(current_user: dict = Depends(get_current_user)):
    """
    Clear all documents from the knowledge base.

    **WARNING**: This is irreversible!
    """
    try:
        count = clear_knowledge_base()
        return {
            "success": True,
            "message": f"Cleared {count} documents from knowledge base",
            "documents_deleted": count,
        }
    except Exception as e:
        logger.error(f"Clear knowledge base error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ================================
# Schema Routes
# ================================
@router.get("/schema/tables")
async def list_database_tables():
    """
    Get list of all tables in the database.
    """
    try:
        tables = get_all_tables()
        return {
            "success": True,
            "tables": tables,
            "count": len(tables),
        }
    except Exception as e:
        logger.error(f"List tables error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/schema/summary")
async def get_database_schema_summary():
    """
    Get high-level summary of database schema.
    """
    try:
        summary = get_schema_summary()
        return {
            "success": True,
            "summary": summary,
        }
    except Exception as e:
        logger.error(f"Schema summary error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ================================
# Health Check Routes
# ================================
@router.get("/health")
async def health_check():
    """
    Check system health.

    Returns status of database connection and other components.
    """
    try:
        # Test database connection
        db_ok = test_connection()

        # Get knowledge base stats
        try:
            kb_stats = get_knowledge_stats()
            kb_ok = True
        except:
            kb_stats = {}
            kb_ok = False

        return {
            "status": "healthy" if db_ok else "unhealthy",
            "components": {
                "database": "ok" if db_ok else "error",
                "knowledge_base": "ok" if kb_ok else "error",
            },
            "knowledge_base_documents": kb_stats.get("total_documents", 0),
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }


@router.get("/audit", response_model=List[Dict[str, Any]])
async def get_audit_log_route(
    limit: int = 50,
    role: Optional[str] = None,
    action: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get recent query audit log entries (admin-only).
    """
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only admin users can access the audit logs."
        )

    from backend.app.db.audit import get_audit_log
    try:
        logs = get_audit_log(limit=limit, role_filter=role, action_filter=action)
        # Format created_at to ISO string and user_id to string for JSON serialization
        formatted_logs = []
        for log in logs:
            log_dict = dict(log)
            if log_dict.get("created_at"):
                log_dict["created_at"] = log_dict["created_at"].isoformat()
            if log_dict.get("user_id"):
                log_dict["user_id"] = str(log_dict["user_id"])
            formatted_logs.append(log_dict)
        return formatted_logs
    except Exception as e:
        logger.error(f"Failed to fetch audit log: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Cognitive Database Agent API",
        "version": "1.0.0",
        "description": "AI-powered database interaction with Row-Level Security",
        "endpoints": {
            "chat": "/api/chat - Interact with the agent",
            "roles": "/api/roles - Get available roles",
            "ingest": "/api/ingest - Ingest schema knowledge",
            "health": "/api/health - Health check",
            "audit": "/api/audit - Get query audit logs (admin-only)",
            "auth_login": "/api/auth/login - Login and retrieve token",
            "auth_me": "/api/auth/me - Retrieve current user profile",
            "docs": "/docs - API documentation",
        },
    }


# ================================
# Export router
# ================================
__all__ = ["router"]
