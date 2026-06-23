# 🧠 Sybil-SQL

### AI-Powered Conversational Database System with Unforgeable Security

> Query, analyze, and manage databases using natural language — **without compromising security**.

---

## 🚀 Overview

**Sybil-SQL** is a full-stack AI application that enables users to interact with a PostgreSQL database using plain English, while enforcing **enterprise-grade security** through **Row-Level Security (RLS)**.

Unlike traditional AI database tools that rely on application-level permission checks, this system enforces access control **directly at the database kernel level**, making privilege escalation **cryptographically and logically impossible**.

The result is a **secure, autonomous, explainable AI agent** capable of querying, modifying, archiving, and visualizing data — all through conversation.

---

## ✨ Key Features

### 🗣️ Natural Language Database Interaction
* Ask questions in plain English — no SQL required
* Supports complex, multi-step operations
* Transparent reasoning using the **ReAct agent pattern**

### 💬 Conversational Session Memory & Local Storage Persistence
* State-managed active sessions mapped by unique conversation UUIDs
* High-fidelity context tracking using a `ConversationBufferWindowMemory` window size of `k=10`
* Session cleanup routines to release inactive agent resources automatically
* Persistent client-side session history caching using `localStorage`
* Interactive sidebar UI drawer to view, switch, rename, or delete past conversations
* Real-time toast notifications for user interactions and success/failure alerts

### ⚡ Real-Time Streaming Responses (SSE)
* Server-Sent Events (SSE) stream reasoning paths, database tool activities, and execution states to the client as they occur
* Interactive typewriter animation effects for final LLM responses

### 📊 Intelligent Data Visualization & Choropleth Maps
* LLM-driven chart type detection with fallback to 11 heuristic rules
* Supports Bar, Line, Area, Pie, Table, and Map/Choropleth views
* Dynamic geographical mapping for regional data (e.g. Cardinal directions maps for North/South/East/West)
* Interactive badges showing whether visual layout was determined by AI reasoning

### 🎯 Schema-Aware Query Suggestions
* Analyzes the active Postgres schema context retrieved via RAG and the current output
* Recommends 3 context-aware, clickable follow-up questions formatted by categories (🔍 Drill-down, ⚖️ Compare, 📈 Trend, 🎯 Filter)

### 🔐 Unforgeable Security (PostgreSQL RLS)
* Database-level Row-Level Security (not app-level)
* Prevents privilege escalation by design
* Role-aware execution: **Admin, Manager, Viewer**
* Zero trust in the AI agent — security is enforced by PostgreSQL itself

### 🤖 Autonomous Cognitive Agent & Model Flexibility
* Pluggable LLM configuration supporting:
  * **Ollama** (Local models like `llama3.1:8b` or `qwen2.5:7b`)
  * **Google Gemini** (Gemini API for production)
  * **OpenAI** (GPT-4o or GPT-4o-mini)
* Uses custom tools for safe DB interaction
* Multi-step planning: select → insert → delete → aggregate
* Role-aware error handling and messaging

### 📚 Retrieval-Augmented Generation (RAG)
* Learns database schema dynamically using embeddings
* No hardcoded schema or prompt engineering
* Scales to large and evolving databases

---

## 🏗️ System Architecture

![Sybil-SQL System Architecture](./Arch.png)

```text
Frontend (React + Vite)
│
│  Chat UI (SSE Stream) + Role Selector + Auto Visualizations (Choropleth/Charts)
│  Interactive Suggestion Chips
▼
Backend (FastAPI)
│
│  Sybil-SQL Agent (LangChain ReAct)
│  ├── DB Tools (role-aware)
│  ├── RAG Retriever (pgvector)
│  ├── Suggestion Engine (Schema Context + Query Analyzer)
│  └── Query Planner
│
▼
PostgreSQL (RLS Enforced)
│
│  sales_data, sales_archive, knowledge_docs
│  Roles: admin | manager | viewer
│  Security: Row-Level Security (Unbypassable)
```

---

## 🧩 Tech Stack

### Frontend
* React 18 / 19 + Vite
* TypeScript / JavaScript
* Recharts + React-Simple-Maps
* Axios

### Backend
* FastAPI
* LangChain (ReAct Agent)
* Ollama / Google Gemini / OpenAI
* Pydantic Settings

### Database
* PostgreSQL 14+
* Row-Level Security (RLS)
* pgvector

### AI / ML
* Sentence Transformers (all-MiniLM-L6-v2)
* Retrieval-Augmented Generation (RAG)

---

## ⚙️ Model & Provider Configuration

The Sybil-SQL agent is fully customizable. You can configure and toggle between local LLM instances and cloud providers via the `.env` configuration file.

### Provider Details & Settings:
* **Google Gemini (Recommended & Configured)**: Leverages Gemini models for fast, accurate generation and reasoning. Uses the Gemini Embeddings API (`models/embedding-001`) with 768 dimensions for pgvector similarity searches.
* **Ollama (Local)**: Runs open-weights models (e.g., `qwen2.5:7b` or `gemma4`) on your local hardware for zero cost and offline capability.
* **OpenAI (Cloud)**: Uses `gpt-4o` or `gpt-4o-mini` with strict JSON constraints.

#### Switching Providers:
To modify the active models or switch provider targets, update the configuration keys in your `.env` file:

```bash
# Google Gemini (Default config)
LLM_PROVIDER=gemini
LLM_MODEL=gemini-flash-latest
GOOGLE_API_KEY=your_gemini_api_key_here
EMBEDDING_MODEL=models/embedding-001
EMBEDDING_DIMENSION=768

# Local Ollama Integration
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:7b
OLLAMA_BASE_URL=http://localhost:11434

# OpenAI Integration
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=your_openai_api_key_here
```

---

## 🔐 Role-Based Access Control

| Role        | Permissions                              |
| ----------- | ---------------------------------------- |
| **Admin**   | Full access, all regions, all operations |
| **Manager** | Read/write access to own region only     |
| **Viewer**  | Read-only access, no mutations allowed   |

**Security is enforced at the database level — not in the application code.**

```sql
CREATE POLICY manager_select_own_region
ON sales_data
FOR SELECT
TO db_manager
USING (region = current_setting('app.current_region'));
```

---

## 📊 Example Queries

```text
"Show total sales by region" -> (Generates Interactive Choropleth Map)
"Archive all 2021 sales from my region"
"Which quarter had the highest sales?"
"Show quarterly trends for 2023"
```

---

## 🧪 Tested & Validated

* RLS privilege escalation attempts blocked
* SQL injection prevention
* Multi-step agent reasoning
* Conversational memory window retention
* SSE streaming connection and resource cleanup
* LLM-first visualization with fallback
* Schema-aware query suggestions

---

## 🚀 Getting Started

### 🐳 Quick Start (Docker Compose)

The easiest way to launch the entire ecosystem (database, local LLM, backend, and frontend) is using Docker Compose:

```bash
# Start all services (Postgres + Ollama + Backend + Frontend)
docker compose up -d

# Wait for Ollama to download the model (~5 min first time)
docker compose logs -f ollama-init

# Ingest database schema context into RAG (one-time setup)
curl -X POST http://localhost:8000/api/ingest

# Open the application
open http://localhost:5173
```

### Services Mapping
| Service  | URL                      | Description          |
|----------|--------------------------|----------------------|
| Frontend | http://localhost:5173     | React Web App        |
| Backend  | http://localhost:8000     | FastAPI Server       |
| API Docs | http://localhost:8000/docs| Interactive API Docs |
| Postgres | localhost:5432           | RLS PostgreSQL DB    |
| Ollama   | http://localhost:11434    | Local LLM Instance   |

---

### Run Locally (Manual Alternative)

### Prerequisites
* Node.js 18+
* Python 3.11+
* PostgreSQL 14+
* Ollama / Gemini API Key / OpenAI API Key

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

```bash
# Frontend
cd frontend
npm install
npm run dev
```

* Frontend: [http://localhost:5173](http://localhost:5173)
* API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### Database Setup

Before running, ensure you have initialized the Postgres database schema and loaded the seed data:

```bash
# Seed the database
psql -h localhost -U postgres -d cognitive_db_agent -f database/schema.sql
psql -h localhost -U postgres -d cognitive_db_agent -f database/seed_data.sql

# Compute embeddings for schemas
PYTHONPATH=. python3 backend/scripts/seed_embeddings.py
```

---

## 📁 Project Structure

```text
backend/
 ├── agent/        # Sybil-SQL agent, tools, suggestions & session manager
 ├── api/          # FastAPI routes and SSE endpoints
 ├── db/           # PostgreSQL connection
 └── core/         # Config & settings

frontend/
 ├── components/   # Visualizer, SuggestionChips, Toast, ConfirmModal & ConversationList
 ├── utils/        # Auto chart logic and user-scoped local storage chatStore
 └── api/          # Backend client & streaming logic

database/
 ├── schema.sql    # Tables + RLS policies
 └── seed_data.sql
```

---

## 📜 License

MIT License

---

## 🙌 Author

* Developed as a University Full-Stack AI Course Project.
* Focused on AI database agents, PostgreSQL security, and modern web systems design.

