"""
Cognitive Database Agent - Configuration Management
====================================================
Centralized configuration using Pydantic Settings.
Loads environment variables from .env file and provides type-safe access.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List
import os


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    # ================================
    # Google Gemini API Configuration
    # ================================
    # Optional: Only needed if using Gemini models (we use sentence-transformers for embeddings)
    google_api_key: str = Field(default="not-needed-for-local-embeddings", env="GOOGLE_API_KEY")

    # ================================
    # Database Configuration
    # ================================
    db_host: str = Field(default="localhost", env="DB_HOST")
    db_port: int = Field(default=5432, env="DB_PORT")
    db_name: str = Field(default="cognitive_db_agent", env="DB_NAME")
    db_user: str = Field(default="postgres", env="DB_USER")
    db_password: str = Field(..., env="DB_PASSWORD")

    # Database Roles
    db_role_admin: str = Field(default="db_admin", env="DB_ROLE_ADMIN")
    db_role_manager: str = Field(default="db_manager", env="DB_ROLE_MANAGER")
    db_role_viewer: str = Field(default="db_viewer", env="DB_ROLE_VIEWER")

    # ================================
    # Vector Embedding Configuration
    # ================================
    embedding_model: str = Field(default="models/embedding-001", env="EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=768, env="EMBEDDING_DIMENSION")

    # ================================
    # LLM Configuration
    # ================================
    # PROVIDER OPTIONS:
    #   "ollama"  → Local model via Ollama (default for development)
    #              Models: llama3.1:8b, qwen2.5:7b, mistral:7b, etc.
    #              Pros: Free, private, no API key needed
    #              Cons: Slower, less accurate, limited context window
    #
    #   "gemini"  → Google Gemini API (recommended for production)
    #              Models: gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash
    #              Requires: GOOGLE_API_KEY environment variable
    #              Pros: Fast, accurate, large context window
    #              Cons: API costs, requires internet
    #
    #   "openai"  → OpenAI API (alternative)
    #              Models: gpt-4o-mini, gpt-4o
    #              Requires: OPENAI_API_KEY environment variable
    #              Pros: Highly accurate, standard API
    #              Cons: API costs, requires internet
    #
    # To switch providers, change LLM_PROVIDER and LLM_MODEL in .env:
    #   LLM_PROVIDER=gemini
    #   LLM_MODEL=gemini-2.0-flash
    # ================================
    llm_provider: str = Field(default="ollama", env="LLM_PROVIDER")  # "ollama", "gemini", or "openai"
    llm_model: str = Field(default="llama3.1:8b", env="LLM_MODEL")
    llm_temperature: float = Field(default=0.1, env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=2048, env="LLM_MAX_TOKENS")
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")

    # ================================
    # FastAPI Configuration
    # ================================
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_reload: bool = Field(default=True, env="API_RELOAD")

    # ================================
    # Security
    # ================================
    secret_key: str = Field(default="dev-secret-key-change-in-production", env="SECRET_KEY")
    jwt_secret_key: str = Field(default="dev-secret-key-change-in-production", env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=60, env="JWT_EXPIRE_MINUTES")

    # CORS Settings
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000", env="CORS_ORIGINS"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # ================================
    # Logging
    # ================================
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # ================================
    # Agent Configuration
    # ================================
    agent_verbose: bool = Field(default=True, env="AGENT_VERBOSE")
    agent_max_iterations: int = Field(default=15, env="AGENT_MAX_ITERATIONS")
    agent_max_execution_time: int = Field(default=120, env="AGENT_MAX_EXECUTION_TIME")
    agent_early_stopping: str = Field(default="force", env="AGENT_EARLY_STOPPING")

    # ================================
    # RAG Configuration
    # ================================
    rag_top_k: int = Field(default=5, env="RAG_TOP_K")
    rag_similarity_threshold: float = Field(default=0.7, env="RAG_SIMILARITY_THRESHOLD")

    # ================================
    # Development Settings
    # ================================
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")

    # ================================
    # Computed Properties
    # ================================
    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def async_database_url(self) -> str:
        """Construct async PostgreSQL connection URL."""
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# ================================
# Global Settings Instance
# ================================
try:
    settings = Settings()
except Exception as e:
    print(f"Error loading settings: {e}")
    print("Make sure you have a .env file with all required variables.")
    print("See .env.example for reference.")
    raise


# ================================
# Helper Functions
# ================================
def get_db_connection_params(role: str = None) -> dict:
    """
    Get database connection parameters.

    Args:
        role: Optional database role to use for connection

    Returns:
        Dictionary with connection parameters
    """
    params = {
        "host": settings.db_host,
        "port": settings.db_port,
        "database": settings.db_name,
        "user": settings.db_user,
        "password": settings.db_password,
    }

    # Note: Role will be set via SET LOCAL ROLE after connection
    return params


def get_role_name(role_type: str) -> str:
    """
    Get the database role name for a given role type.

    Args:
        role_type: One of 'admin', 'manager', 'viewer'

    Returns:
        Database role name

    Raises:
        ValueError: If role_type is invalid
    """
    role_mapping = {
        "admin": settings.db_role_admin,
        "manager": settings.db_role_manager,
        "viewer": settings.db_role_viewer,
    }

    if role_type.lower() not in role_mapping:
        raise ValueError(
            f"Invalid role type: {role_type}. Must be one of {list(role_mapping.keys())}"
        )

    return role_mapping[role_type.lower()]


# ================================
# Export public API
# ================================
__all__ = ["settings", "Settings", "get_db_connection_params", "get_role_name"]
