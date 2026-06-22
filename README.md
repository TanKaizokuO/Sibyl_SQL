# 🧠 Sibyl_SQL

### AI-Powered Conversational Database System with Unforgeable Security

> Query, analyze, and manage databases using natural language — **without compromising security**.

---

## 🚀 Overview

**Sibyl_SQL** is a full-stack AI application that enables users to interact with a PostgreSQL database using plain English, while enforcing **enterprise-grade security** through **Row-Level Security (RLS)**.

Unlike traditional AI database tools that rely on application-level permission checks, this system enforces access control **directly at the database kernel level**, making privilege escalation **cryptographically and logically impossible**.

The result is a **secure, autonomous, explainable AI agent** capable of querying, modifying, archiving, and visualizing data — all through conversation.

---

## ✨ Key Features

### 🗣️ Natural Language Database Interaction
* Ask questions in plain English — no SQL required
* Supports complex, multi-step operations
* Transparent reasoning using the **ReAct agent pattern**

### 💬 Conversational Session Memory
* State-managed active sessions mapped by unique conversation UUIDs
* High-fidelity context tracking using a `ConversationBufferWindowMemory` window size of `k=10`
* Session cleanup routines to release inactive agent resources automatically

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

```text
Frontend (React + Vite)
│
│  Chat UI (SSE Stream) + Role Selector + Auto Visualizations (Choropleth/Charts)
│  Interactive Suggestion Chips
▼
Backend (FastAPI)
│
│  Session Manager (Active Sessions & Memory Window)
│  Cognitive Agent (LangChain ReAct)
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

The Sibyl_SQL agent is fully customizable. You can configure and toggle between local LLM instances and cloud providers via the `.env` configuration file.

### Trade-offs:
* **Development (Local)**: Ollama with local models (completely free, private, offline-capable, slower processing).
* **Production (Cloud)**: Google Gemini or OpenAI APIs (highly accurate, fast inference, supports larger context windows).

#### Switching Providers:
To switch between providers, modify the `LLM_PROVIDER` and `LLM_MODEL` variables in your `.env` file:

```bash
# To run local Ollama
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b

# To run Google Gemini (Recommended for production)
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash
GOOGLE_API_KEY=your_gemini_api_key_here

# To run OpenAI
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

### Prerequisites
* Node.js 18+
* Python 3.11+
* PostgreSQL 14+
* Ollama / Gemini API Key / OpenAI API Key

### Run Locally

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

---

## 📁 Project Structure

```text
backend/
 ├── agent/        # Sibyl_SQL agent, tools, suggestions & session manager
 ├── api/          # FastAPI routes and SSE endpoints
 ├── db/           # PostgreSQL connection
 └── core/         # Config & settings

frontend/
 ├── components/   # Visualizer, SuggestionChips & UI components
 ├── utils/        # Auto chart logic with LLM priority
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

