# Phase 1 — Security Hardening & Audit Trail

> **Items covered:** #1 (JWT Auth), #2 (SQL Query Validator), #5 (Audit Log)
> **Rationale:** These three items are tightly coupled — authentication determines *who* you are, the query validator constrains *what* you can do, and the audit log records *everything* that happened. Implementing them together produces a complete, end-to-end security vertical.

---

## 1.1 JWT Authentication (Item #1)

### Problem
The role switcher in the frontend (`App.jsx:141-164`) lets anyone freely choose Admin/Manager/Viewer. The role and region are sent as plain fields in the `POST /api/chat` request body (`frontend/src/api/agent.js:14-18`). The backend (`backend/app/api/routes/agent.py:84-107`) trusts whatever the client sends and passes it directly to `create_agent()`. This means RLS enforcement at the Postgres level is real, but **who gets which role** is entirely unguarded.

### Changes Required

#### Database Layer
- **File:** `database/07_create_auth_tables.sql` (NEW)
  - Create `auth_users` table: `id UUID PK`, `username VARCHAR UNIQUE`, `email VARCHAR UNIQUE`, `password_hash VARCHAR`, `role VARCHAR` (references `roles.role_name`), `region VARCHAR NULL`, `is_active BOOLEAN`, `created_at TIMESTAMP`, `updated_at TIMESTAMP`
  - Seed 3 demo users:
    - `admin_user` / password `admin123` / role `admin` / region `NULL`
    - `north_manager` / password `manager123` / role `manager` / region `North`
    - `viewer_user` / password `viewer123` / role `viewer` / region `NULL`

#### Backend Layer

- **File:** `backend/app/core/config.py`
  - Add settings:
    - `jwt_secret_key: str` (use existing `secret_key` or add new one)
    - `jwt_algorithm: str = "HS256"`
    - `jwt_expire_minutes: int = 60`

- **File:** `backend/app/core/auth.py` (NEW)
  - Dependencies: `python-jose[cryptography]` (already in `requirements.txt`), `passlib[bcrypt]` (already in `requirements.txt`)
  - Functions:
    - `hash_password(password: str) -> str` — bcrypt hash
    - `verify_password(plain: str, hashed: str) -> bool`
    - `create_access_token(data: dict, expires_delta: timedelta = None) -> str` — encode `sub` (user_id), `role`, `region`, `exp` into JWT
    - `decode_access_token(token: str) -> dict` — decode and validate JWT, raise `HTTPException(401)` on failure
    - `get_current_user(token: str = Depends(oauth2_scheme)) -> dict` — FastAPI dependency that extracts user info from the `Authorization: Bearer <token>` header

- **File:** `backend/app/api/routes/auth.py` (NEW)
  - `POST /api/auth/login` — accepts `{username, password}`, validates against `auth_users` table, returns `{access_token, token_type, role, region}`
  - `GET /api/auth/me` — returns current user info from JWT (protected endpoint)

- **File:** `backend/app/api/routes/agent.py` (MODIFY)
  - Add `Depends(get_current_user)` to `chat_with_agent`, `ingest_knowledge`, `add_custom_knowledge_document`, `clear_knowledge`
  - **Critical change:** Replace `request.role` and `request.region` with values from the JWT token. The `ChatRequest` model should no longer accept `role` and `region` fields — these come from the verified token only.
  - Remove the `role` field from `ChatRequest` or make it ignored
  - The agent is now created with `create_agent(role=current_user["role"], region=current_user["region"])`

- **File:** `backend/main.py` (MODIFY)
  - Register the new `auth_router` alongside `agent_router`
  - Add the auth endpoints to the root endpoint's API listing

#### Frontend Layer

- **File:** `frontend/src/api/agent.js` (MODIFY)
  - Add `login(username, password)` function that calls `POST /api/auth/login` and stores the JWT in localStorage
  - Modify the axios instance to include `Authorization: Bearer <token>` header from localStorage
  - Add `logout()` function that clears localStorage
  - Remove `role` and `region` from the `chatWithAgent` request body (these are now derived from the JWT)

- **File:** `frontend/src/components/LoginForm.jsx` (NEW)
  - Simple login form with username/password fields
  - On successful login, store token and redirect to chat
  - Display the logged-in user's role and region in the UI

- **File:** `frontend/src/App.jsx` (MODIFY)
  - Add auth state management (`isLoggedIn`, `currentUser`)
  - Show `LoginForm` when not authenticated, chat interface when authenticated
  - Replace the role/region `<select>` dropdowns with a display of the current user's role (from the JWT). The user can no longer switch roles — their role is fixed by their login credentials.
  - Add a Logout button in the header

---

## 1.2 SQL Query Validator / Allowlist (Item #2)

### Problem
The 6 tools in `backend/app/agent/tools.py` do basic statement-type checks (e.g., `run_secure_query_func` checks `query.startswith("SELECT")`) but the LLM constructs the SQL body freely. A crafted prompt could make the LLM generate destructive SQL like `SELECT * FROM sales_data; DROP TABLE sales_data;` (statement stacking) or `DELETE FROM sales_data` through the wrong tool.

### Changes Required

- **File:** `backend/app/agent/query_validator.py` (NEW)
  - Class `QueryValidator`:
    - **Blocklist:** Reject any query containing `DROP`, `TRUNCATE`, `ALTER`, `CREATE`, `GRANT`, `REVOKE`, `COPY`, `EXECUTE`, `SET ROLE` (prevent role escalation), `SET LOCAL ROLE` (only the connection manager should do this)
    - **Statement stacking detection:** Reject queries containing `;` followed by another statement (split on `;`, check if > 1 non-empty statement)
    - **Subquery depth limit:** Reject queries with more than 3 levels of nested subqueries
    - **Comment stripping:** Strip SQL comments (`--`, `/* */`) before validation to prevent bypass
    - Method `validate(query: str, allowed_type: str) -> Tuple[bool, str]` returns `(is_valid, rejection_reason)`
  - **Dry-run mode:**
    - Add a `dry_run: bool = False` parameter to `ChatRequest` in `routes/agent.py`
    - When `dry_run=True`, the agent generates the SQL plan and returns it **without executing** — the user sees what SQL would run
    - The tool functions should check a `dry_run` flag and return the planned SQL instead of executing it
  - **Rate limiting per role:**
    - Simple in-memory rate limiter (dict of `{role: [timestamps]}`)
    - Viewer: max 30 queries/minute
    - Manager: max 60 queries/minute
    - Admin: max 120 queries/minute
    - Return `HTTP 429` when exceeded

- **File:** `backend/app/agent/tools.py` (MODIFY)
  - Import and call `QueryValidator.validate()` at the top of each tool function (`run_secure_query_func`, `run_secure_insert_func`, `run_secure_update_func`, `run_secure_delete_func`) before executing the query
  - If validation fails, return a JSON error explaining why the query was rejected

---

## 1.3 Query Audit Log (Item #5)

### Problem
The project claims "auditable" as a feature but there's no audit trail. Every query that the agent executes should be logged for compliance and debugging.

### Changes Required

#### Database Layer
- **File:** `database/08_create_audit_log.sql` (NEW)
  ```sql
  CREATE TABLE audit_log (
      id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
      user_id UUID,           -- from JWT (NULL for unauthenticated)
      role VARCHAR(50),       -- role used for execution
      region VARCHAR(50),     -- region context
      action VARCHAR(20),     -- 'SELECT', 'INSERT', 'UPDATE', 'DELETE'
      tool_name VARCHAR(50),  -- which agent tool was used
      sql_query TEXT,         -- the actual SQL executed
      row_count INTEGER,      -- rows returned/affected
      success BOOLEAN,        -- did it succeed?
      error_message TEXT,     -- error if failed
      execution_time_ms INTEGER, -- how long it took
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);
  CREATE INDEX idx_audit_log_role ON audit_log(role);
  CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
  ```

#### Backend Layer
- **File:** `backend/app/db/audit.py` (NEW)
  - Function `log_query(user_id, role, region, action, tool_name, sql_query, row_count, success, error_message, execution_time_ms)` — inserts a row into `audit_log`
  - Function `get_audit_log(limit=50, role_filter=None, action_filter=None) -> List[Dict]` — retrieves recent audit entries

- **File:** `backend/app/agent/tools.py` (MODIFY)
  - In each tool function, wrap the query execution in timing logic (`time.time()` before and after)
  - After execution (success or failure), call `log_query(...)` with all relevant metadata
  - The user_id should come from thread-local or context variable set by the API route

- **File:** `backend/app/api/routes/agent.py` (MODIFY)
  - Add `GET /api/audit` endpoint (admin-only) that returns recent audit log entries
  - Accept query params: `limit`, `role`, `action`

#### Frontend Layer (optional for this phase)
- No mandatory frontend changes — the audit log is primarily a backend/DB feature
- Optionally, add an "Audit Log" tab visible only to admin users

---

## Verification Plan

1. **Auth flow:** Login with each demo user → verify JWT contains correct role/region → verify chat endpoint rejects requests without a valid token → verify role in JWT matches what the agent uses (not user-supplied)
2. **Query validator:** Attempt to send a chat message that triggers `DROP TABLE` → verify it's blocked → attempt statement stacking → verify it's blocked → test dry-run mode returns SQL without executing
3. **Rate limiting:** Send 35 rapid queries as viewer → verify 429 response after the 30th
4. **Audit log:** Send 5 different queries → query the `audit_log` table → verify all 5 are logged with correct metadata → verify the `GET /api/audit` endpoint returns them
5. **Integration:** Login as manager (North) → ask "show all sales data" → verify RLS filters to North region → verify audit log shows the query with role=manager, region=North
