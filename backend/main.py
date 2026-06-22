"""
Cognitive Database Agent - Main FastAPI Application
===================================================
Entry point for the FastAPI server.

Run with:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger as loguru_logger
import sys

from backend.app.core.config import settings
from backend.app.api.routes.agent import router as agent_router
from backend.app.api.routes.auth import router as auth_router


# ================================
# Logging Configuration
# ================================
def setup_logging():
    """Configure logging with loguru."""
    # Remove default handler
    loguru_logger.remove()

    # Add custom handler
    loguru_logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level,
    )

    # Bridge Python logging to loguru
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            try:
                level = loguru_logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            loguru_logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )

    # Setup logging
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO)


# Initialize logging
setup_logging()


# ================================
# FastAPI Application
# ================================
app = FastAPI(
    title="Cognitive Database Agent API",
    description="""
    AI-powered database interaction system with Row-Level Security.

    **Features:**
    - Multi-step planning with LangChain and Google Gemini
    - Row-Level Security (RLS) enforcement
    - Retrieval-Augmented Generation (RAG) for schema understanding
    - Role-based access control (Admin, Manager, Viewer)

    **Technology Stack:**
    - LLM: Google Gemini (gemini-1.5-flash)
    - Framework: LangChain
    - Database: PostgreSQL + pgvector
    - Security: Native PostgreSQL RLS
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ================================
# CORS Middleware
# ================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ================================
# Include Routers
# ================================
app.include_router(agent_router)
app.include_router(auth_router)


# ================================
# Startup/Shutdown Events
# ================================
@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    loguru_logger.info("=" * 60)
    loguru_logger.info("Cognitive Database Agent - Starting Up")
    loguru_logger.info("=" * 60)
    loguru_logger.info(f"Environment: {settings.environment}")
    loguru_logger.info(f"Debug Mode: {settings.debug}")
    loguru_logger.info(f"API Host: {settings.api_host}:{settings.api_port}")
    loguru_logger.info(f"LLM Model: {settings.llm_model}")
    loguru_logger.info(f"Embedding Model: {settings.embedding_model}")
    loguru_logger.info(f"Database: {settings.db_host}:{settings.db_port}/{settings.db_name}")
    loguru_logger.info(f"CORS Origins: {settings.cors_origins_list}")
    loguru_logger.info("=" * 60)

    # Test database connection
    from backend.app.db.connection import test_connection

    if test_connection():
        loguru_logger.success("✓ Database connection successful")
    else:
        loguru_logger.error("✗ Database connection failed")

    loguru_logger.info("Application ready to serve requests")
    loguru_logger.info("API Documentation: http://localhost:8000/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    loguru_logger.info("=" * 60)
    loguru_logger.info("Cognitive Database Agent - Shutting Down")
    loguru_logger.info("=" * 60)

    # Close database connections
    from backend.app.db.connection import close_pool

    close_pool()
    loguru_logger.info("✓ Database connections closed")
    loguru_logger.info("Goodbye!")


# ================================
# Root Endpoint
# ================================
@app.get("/")
async def root():
    """Root endpoint with welcome message."""
    return {
        "message": "Welcome to Cognitive Database Agent API",
        "version": "1.0.0",
        "status": "online",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
        },
        "api_endpoints": {
            "chat": "/api/chat",
            "roles": "/api/roles",
            "health": "/api/health",
            "schema": "/api/schema/tables",
            "ingest": "/api/ingest",
        },
    }


# ================================
# Health Check
# ================================
@app.get("/ping")
async def ping():
    """Simple health check endpoint."""
    return {"status": "pong"}


# ================================
# Run Application
# ================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )
