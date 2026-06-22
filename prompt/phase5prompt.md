# Phase 5 — Docker Compose & Production Readiness

> **Items covered:** #9 (Docker Compose Setup)
> **Rationale:** This is the final phase because it wraps everything from Phases 1-4 into a reproducible, one-command deployment. It should be done last so the Dockerfiles capture the complete, final state of the application.

---

## 5.1 Docker Compose Setup (Item #9)

### Problem
The README currently requires manual setup of PostgreSQL, Ollama, Python virtualenv, Node.js, and correct environment configuration. This is error-prone and makes the project hard to evaluate. A `docker-compose.yml` would make the entire system launchable with a single `docker compose up` command.

### Changes Required

#### Root Level Files

- **File:** `docker-compose.yml` (NEW)
  ```yaml
  version: "3.9"
  
  services:
    # ================================
    # PostgreSQL with pgvector
    # ================================
    postgres:
      image: pgvector/pgvector:pg16
      container_name: neurodb-postgres
      environment:
        POSTGRES_DB: cognitive_db_agent
        POSTGRES_USER: postgres
        POSTGRES_PASSWORD: ${DB_PASSWORD:-neurodb_dev_password}
      ports:
        - "5432:5432"
      volumes:
        - postgres_data:/var/lib/postgresql/data
        - ./database:/docker-entrypoint-initdb.d  # Auto-run SQL files on first start
      healthcheck:
        test: ["CMD-SHELL", "pg_isready -U postgres -d cognitive_db_agent"]
        interval: 5s
        timeout: 5s
        retries: 10
      networks:
        - neurodb-network

    # ================================
    # Ollama LLM Server
    # ================================
    ollama:
      image: ollama/ollama:latest
      container_name: neurodb-ollama
      ports:
        - "11434:11434"
      volumes:
        - ollama_data:/root/.ollama
      healthcheck:
        test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
        interval: 10s
        timeout: 5s
        retries: 5
      networks:
        - neurodb-network
      # GPU support (uncomment if NVIDIA GPU available):
      # deploy:
      #   resources:
      #     reservations:
      #       devices:
      #         - driver: nvidia
      #           count: 1
      #           capabilities: [gpu]

    # ================================
    # Model Loader (one-shot init container)
    # ================================
    ollama-init:
      image: curlimages/curl:latest
      container_name: neurodb-ollama-init
      depends_on:
        ollama:
          condition: service_healthy
      entrypoint: >
        sh -c "
          echo 'Pulling LLM model...' &&
          curl -s http://ollama:11434/api/pull -d '{\"name\": \"llama3.1:8b\"}' &&
          echo 'Model ready!'
        "
      networks:
        - neurodb-network

    # ================================
    # FastAPI Backend
    # ================================
    backend:
      build:
        context: .
        dockerfile: backend/Dockerfile
      container_name: neurodb-backend
      environment:
        - DB_HOST=postgres
        - DB_PORT=5432
        - DB_NAME=cognitive_db_agent
        - DB_USER=postgres
        - DB_PASSWORD=${DB_PASSWORD:-neurodb_dev_password}
        - LLM_PROVIDER=${LLM_PROVIDER:-ollama}
        - LLM_MODEL=${LLM_MODEL:-llama3.1:8b}
        - OLLAMA_BASE_URL=http://ollama:11434
        - GOOGLE_API_KEY=${GOOGLE_API_KEY:-not-needed-for-ollama}
        - SECRET_KEY=${SECRET_KEY:-docker-dev-secret-key-change-in-production}
        - CORS_ORIGINS=http://localhost:5173,http://localhost:3000
        - ENVIRONMENT=development
        - LOG_LEVEL=INFO
      ports:
        - "8000:8000"
      depends_on:
        postgres:
          condition: service_healthy
        ollama:
          condition: service_healthy
      networks:
        - neurodb-network
      restart: unless-stopped

    # ================================
    # React Frontend (Vite dev server)
    # ================================
    frontend:
      build:
        context: ./frontend
        dockerfile: Dockerfile
      container_name: neurodb-frontend
      environment:
        - VITE_API_URL=http://localhost:8000
      ports:
        - "5173:5173"
      depends_on:
        - backend
      networks:
        - neurodb-network
      restart: unless-stopped

  # ================================
  # Volumes
  # ================================
  volumes:
    postgres_data:
      name: neurodb-postgres-data
    ollama_data:
      name: neurodb-ollama-data

  # ================================
  # Networks
  # ================================
  networks:
    neurodb-network:
      name: neurodb-network
      driver: bridge
  ```

- **File:** `backend/Dockerfile` (NEW)
  ```dockerfile
  FROM python:3.11-slim
  
  WORKDIR /app
  
  # Install system dependencies for psycopg2 and PyTorch
  RUN apt-get update && apt-get install -y \
      build-essential \
      libpq-dev \
      curl \
      && rm -rf /var/lib/apt/lists/*
  
  # Copy requirements and install Python dependencies
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  
  # Copy application code
  COPY . .
  
  # Create .env file for Docker (overridden by docker-compose environment)
  RUN echo "DB_PASSWORD=neurodb_dev_password" > .env
  
  # Expose port
  EXPOSE 8000
  
  # Run with uvicorn
  CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
  ```

- **File:** `frontend/Dockerfile` (NEW)
  ```dockerfile
  FROM node:20-alpine
  
  WORKDIR /app
  
  # Copy package files
  COPY package.json package-lock.json ./
  
  # Install dependencies
  RUN npm ci
  
  # Copy source code
  COPY . .
  
  # Expose Vite dev server port
  EXPOSE 5173
  
  # Run Vite dev server (accessible from outside container)
  CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
  ```

- **File:** `.dockerignore` (NEW)
  ```
  # Python
  __pycache__
  *.pyc
  *.pyo
  .venv
  venv
  .pytest_cache
  .mypy_cache
  
  # Node
  node_modules
  frontend/node_modules
  
  # IDE
  .vscode
  .idea
  
  # Git
  .git
  .gitignore
  
  # Environment
  .env
  .env.local
  
  # Docker
  docker-compose.yml
  ```

- **File:** `frontend/.dockerignore` (NEW)
  ```
  node_modules
  dist
  .git
  ```

---

## 5.2 Database Initialization Script

### Problem
The SQL files in `database/` are numbered `01` through `06`. Docker's `docker-entrypoint-initdb.d` runs them in alphabetical order, which is correct. However, we need to ensure:
1. The `01_setup_extensions.sql` runs first (creates `uuid-ossp`, `pgvector` extensions)
2. The `02_create_tables.sql` runs next (creates all tables)
3. The `03_insert_sample_data.sql` inserts sample data
4. The `04_create_rls_policies.sql` sets up RLS
5. Any new files from Phase 1 (`07_create_auth_tables.sql`, `08_create_audit_log.sql`) are included

### Changes Required

- **File:** `database/00_init.sh` (NEW)
  - A wrapper script that runs all SQL files in order:
    ```bash
    #!/bin/bash
    set -e
    
    echo "=== NeuroDB Database Initialization ==="
    
    for f in /docker-entrypoint-initdb.d/*.sql; do
      echo "Running: $f"
      psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$f"
    done
    
    echo "=== Database initialization complete ==="
    ```
  - This ensures predictable ordering even if Docker's initdb behavior changes

---

## 5.3 Docker-Specific README Updates

- **File:** `README.md` (MODIFY)
  - Add a prominent "Quick Start (Docker)" section at the top:
    ```markdown
    ## 🐳 Quick Start (Docker)
    
    ```bash
    # Clone the repository
    git clone https://github.com/your-repo/NeuroDB.git
    cd NeuroDB
    
    # Start everything (Postgres + Ollama + Backend + Frontend)
    docker compose up -d
    
    # Wait for Ollama to download the model (~5 min first time)
    docker compose logs -f ollama-init
    
    # Ingest schema knowledge (one-time)
    curl -X POST http://localhost:8000/api/ingest
    
    # Open the app
    open http://localhost:5173
    ```
    
    ### Services
    | Service  | URL                      | Description          |
    |----------|--------------------------|----------------------|
    | Frontend | http://localhost:5173     | React UI             |
    | Backend  | http://localhost:8000     | FastAPI API          |
    | API Docs | http://localhost:8000/docs| Swagger UI           |
    | Postgres | localhost:5432           | Database             |
    | Ollama   | http://localhost:11434    | LLM Server           |
    ```
  - Keep the existing manual setup instructions below, clearly labeled as "Manual Setup (Alternative)"

- **File:** `.env.docker` (NEW)
  - A Docker-specific env file with sensible defaults:
    ```env
    DB_PASSWORD=neurodb_dev_password
    LLM_PROVIDER=ollama
    LLM_MODEL=llama3.1:8b
    SECRET_KEY=docker-dev-secret-key-change-in-production
    ```

---

## 5.4 Production Build Variant

- **File:** `docker-compose.prod.yml` (NEW — optional override)
  - Overrides for production:
    - Frontend: multi-stage build with `npm run build` + nginx to serve static files
    - Backend: no `--reload` flag, production log level
    - Postgres: stronger password, no exposed port
  - Usage: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`

---

## Verification Plan

### Docker Setup
1. From a clean machine (no local Postgres/Ollama), run `docker compose up -d` → verify all 4 services start
2. Check `docker compose ps` → all services should be "healthy" or "running"
3. Wait for `ollama-init` to complete → verify the LLM model is pulled
4. Run `curl -X POST http://localhost:8000/api/ingest` → verify schema ingestion succeeds
5. Open `http://localhost:5173` → verify the frontend loads
6. Send a chat message → verify end-to-end flow works through Docker networking
7. Run `docker compose down` → verify clean shutdown
8. Run `docker compose up -d` again → verify data persists (Postgres volume)

### Dockerfiles
1. `docker build -f backend/Dockerfile .` → verify it builds without errors
2. `docker build -f frontend/Dockerfile frontend/` → verify it builds without errors
3. Verify `.dockerignore` excludes `node_modules`, `.env`, `__pycache__`

### README
1. Follow the "Quick Start (Docker)" instructions from scratch → verify it's accurate and complete
2. Verify the services table matches actual ports
