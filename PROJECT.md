# Sybil-SQL

## Overview
**Vision/Goal:** Sybil-SQL is a full-stack AI application that enables users to query, analyze, and visualize a PostgreSQL database using plain English, enforcing unforgeable security through Row-Level Security (RLS) directly at the database kernel level.

**Current Status:** Active Development

## Tech Stack
**Language/Runtime:** Python 3.11+, Node.js 18+

**Frameworks/Libraries:** 
- Frontend: React 19, Vite, Recharts, React-Simple-Maps
- Backend: FastAPI, LangChain (ReAct Agent pattern)

**Key Dependencies:** 
- PostgreSQL 14+ with `pgvector` (Vector store and RLS enforcement)
- Pluggable LLMs (Ollama for local, Google Gemini/OpenAI for cloud)
- Sentence Transformers (`all-MiniLM-L6-v2`) for RAG schema embeddings

## Directory Structure
```text
backend/
 ├── app/
 │    ├── agent/        # LangChain ReAct agent, custom DB tools, schema suggestions
 │    ├── api/          # FastAPI routes and SSE streaming endpoints
 │    ├── db/           # PostgreSQL connection management
 │    └── core/         # Pydantic configuration & environment settings
 ├── scripts/           # DB seeding and pgvector embeddings generation
frontend/
 ├── src/
 │    ├── components/   # UI elements (Visualizer, SuggestionChips, Toast, ConversationList)
 │    ├── utils/        # Auto chart heuristics and localStorage chatStore
 │    ├── api/          # Axios backend client & SSE connection logic
 │    └── App.jsx       # Main application container
database/
 ├── schema.sql         # Postgres tables and RLS security policies
 └── seed_data.sql      # Initial test data
```

## Core Logic & Data Flow
1. **Natural Language Query Execution & RLS:** A user submits a query via the frontend. The FastAPI backend passes it to a LangChain ReAct agent, which fetches relevant database schema context via `pgvector` (RAG). The agent writes and executes SQL using custom database tools. Execution is role-aware (Admin/Manager/Viewer), relying completely on Postgres Row-Level Security (RLS) to enforce access control, blocking unauthorized operations at the kernel level.
2. **Real-Time SSE Streaming:** As the agent plans, searches, and executes queries, intermediate reasoning steps and tool execution states are streamed back to the React frontend in real-time using Server-Sent Events (SSE), providing transparent observability.
3. **Autonomous Data Visualization:** Once the agent returns structured data, the frontend analyzes the data shape and dynamically selects the best visualization (Bar, Line, Area, Pie, Table, or Choropleth Maps) using heuristic rules and Recharts/React-Simple-Maps.

## Environment & Setup
**Prerequisites:** Docker Compose (recommended), OR Node.js 18+, Python 3.11+, PostgreSQL 14+.

**Environment Variables:** Configured via `.env`
- `LLM_PROVIDER` (gemini | ollama | openai)
- `LLM_MODEL` (e.g., gemini-flash-latest, qwen2.5:7b)
- `GOOGLE_API_KEY` / `OPENAI_API_KEY`
- `EMBEDDING_MODEL` (e.g., models/embedding-001)

**Essential Start Commands:**
```bash
# Using Docker (Preferred)
docker compose up -d
curl -X POST http://localhost:8000/api/ingest # Ingest schema to RAG

# Manual Setup (Alternative)
cd backend && pip install -r requirements.txt && uvicorn backend.main:app --reload
cd frontend && npm install && npm run dev
psql -U postgres -d cognitive_db_agent -f database/schema.sql
```

## Development Conventions
- **State Management:** Session memory is managed actively on the backend via a `ConversationBufferWindowMemory` mapped by conversation UUIDs. On the client side, conversation history is persisted using `localStorage`.
- **Security Paradigm:** "Zero Trust" in the application layer or LLM. All authorization and scoping are enforced via PostgreSQL RLS policies (e.g., `USING (region = current_setting('app.current_region'))`).
- **Extensibility:** The backend LLM integration is provider-agnostic. Adding models requires updating configuration in `app/core/config.py` rather than rewriting prompt logic.

## Known Issues / Debt
- **Frontend State Persistence:** Session history relies heavily on client-side `localStorage`, meaning conversations are isolated to the specific browser and device.
- **Visualization Brittleness:** The autonomous chart rendering depends on the LLM outputting predictable JSON schema formats. If the LLM generates edge-case aliases or unexpected column types, the heuristic fallback may default to simple tables instead of rich charts.
- **RAG Context Limits:** Highly complex queries spanning many tables depend entirely on the semantic search retrieving the correct schema definitions. Missing or poorly embedded schema context can degrade the generated SQL quality.
