# Phase 2 — Conversational Memory & Streaming Responses

> **Items covered:** #3 (Conversation History), #4 (Streaming Agent Responses)
> **Rationale:** These two items form a complete "interaction quality" vertical. Memory makes the agent genuinely conversational, and streaming makes it feel responsive. Together they transform the UX from "submit a query and wait" to "have a real-time conversation."

---

## 2.1 Conversation History / Memory (Item #3)

### Problem
The agent appears stateless between turns. Looking at `backend/app/api/routes/agent.py:103-107`, a new `CognitiveAgent` is created on **every request** via `create_agent()`. The agent class does initialize `ConversationBufferMemory` in `cognitive_agent.py:174-180`, but since the agent object is destroyed after each request, the memory is lost. Users can't say "now filter that by Q2" as a follow-up.

### Changes Required

#### Backend Layer

- **File:** `backend/app/agent/cognitive_agent.py` (MODIFY)
  - Switch from `ConversationBufferMemory` to `ConversationBufferWindowMemory` with `k=10` (keep last 10 exchanges to avoid context window overflow)
  - The memory should be initialized with `input_key="input"`, `output_key="output"`, `memory_key="chat_history"`, `return_messages=True`
  - Add `chat_history` to the prompt's `input_variables` list
  - Modify the `AGENT_PROMPT_TEMPLATE` to include a conversation history section:
    ```
    CONVERSATION HISTORY:
    {chat_history}
    
    Use this history to understand follow-up questions. If the user says "filter that", "show me more", 
    "now by region", etc., refer to the previous query context.
    ```

- **File:** `backend/app/agent/session_manager.py` (NEW)
  - Class `SessionManager`:
    - Uses an in-memory dictionary: `Dict[str, CognitiveAgent]` keyed by `session_id`
    - `get_or_create_agent(session_id: str, role: str, region: str | None) -> CognitiveAgent`
      - If `session_id` exists and role matches → return existing agent (preserves memory)
      - If `session_id` exists but role changed → destroy old agent, create new one
      - If `session_id` doesn't exist → create new agent, store it
    - `destroy_session(session_id: str)` — remove agent from memory
    - `cleanup_stale_sessions(max_age_minutes: int = 30)` — remove sessions older than 30 minutes
    - Each agent entry stores: `{ agent: CognitiveAgent, role: str, region: str, last_accessed: datetime }`
  - Thread safety: Use `threading.Lock` for dict access since FastAPI is async

- **File:** `backend/app/api/routes/agent.py` (MODIFY)
  - Import `SessionManager` and create a global instance
  - In `chat_with_agent()`:
    - Generate `session_id` from JWT user_id (or use `conversation_id` from request if provided)
    - Replace `create_agent(...)` with `session_manager.get_or_create_agent(session_id, role, region)`
    - The agent now persists between requests for the same session
  - Add `DELETE /api/session` endpoint to clear a user's session (reset conversation)
  - Add a periodic cleanup (FastAPI background task or `on_event("startup")` scheduler) that calls `cleanup_stale_sessions()` every 5 minutes

- **File:** `backend/app/api/routes/agent.py` (MODIFY — ChatRequest model)
  - Keep the `conversation_id` field (already exists) — use it as session key
  - If not provided, auto-generate one from the user_id

#### Frontend Layer

- **File:** `frontend/src/api/agent.js` (MODIFY)
  - Generate a `conversation_id` (UUID) on app load, store in state
  - Send `conversation_id` with every chat request
  - Add `resetConversation()` function that calls `DELETE /api/session` and generates a new `conversation_id`

- **File:** `frontend/src/App.jsx` (MODIFY)
  - Add a "New Conversation" / "Reset" button in the header that calls `resetConversation()` and clears the local `messages` array
  - Persist `conversation_id` in `useState` (reset when user clicks "New Conversation")

---

## 2.2 Streaming Agent Responses (Item #4)

### Problem
The 2–5 second latency between sending a query and seeing a response makes the system feel sluggish. The frontend shows a "Thinking..." spinner (`App.jsx:214-221`) but provides no progressive feedback. The backend has a `stream_run()` method in `cognitive_agent.py:312-333` but it's a stub that just yields the final result.

### Changes Required

#### Backend Layer

- **File:** `backend/app/agent/cognitive_agent.py` (MODIFY)
  - Implement real streaming in `stream_run()` using LangChain's callback system:
    - Create a `StreamingCallback(BaseCallbackHandler)` class:
      - `on_agent_action(action)` → yield `{"type": "thought", "content": action.log}`
      - `on_tool_start(tool_name, input)` → yield `{"type": "tool_start", "tool": tool_name, "input": input}`
      - `on_tool_end(output)` → yield `{"type": "tool_result", "output": output}`
      - `on_agent_finish(finish)` → yield `{"type": "final_answer", "content": finish.return_values["output"]}`
    - The callback puts events into an `asyncio.Queue`
    - `stream_run()` becomes an async generator that reads from the queue

- **File:** `backend/app/api/routes/agent.py` (MODIFY)
  - Add `POST /api/chat/stream` endpoint that returns a `StreamingResponse` with `media_type="text/event-stream"` (Server-Sent Events)
  - Each SSE event is a JSON object with a `type` field matching the callback events above
  - Format: `data: {"type": "thought", "content": "I need to check the schema..."}\n\n`
  - Final event: `data: {"type": "done"}\n\n`
  - The non-streaming `POST /api/chat` endpoint continues to work as before (backward compatible)

- **File:** `backend/main.py` (MODIFY)
  - No changes needed if the route is added to the existing agent router

#### Frontend Layer

- **File:** `frontend/src/api/agent.js` (MODIFY)
  - Add `chatWithAgentStream(message, conversationId, onEvent)` function:
    - Uses `fetch()` with `ReadableStream` (not axios, since axios doesn't support SSE well)
    - Parses SSE events line by line
    - Calls `onEvent(eventData)` for each parsed event
    - Returns a promise that resolves when the stream ends

- **File:** `frontend/src/App.jsx` (MODIFY)
  - Replace the `handleSubmit` function to use streaming:
    - When submit is clicked, immediately add a "thinking" assistant message
    - As `thought` events arrive, update the intermediate steps in real-time
    - As `tool_start` / `tool_result` events arrive, append to the thinking display
    - When `final_answer` arrives, update the message content
  - The existing `renderIntermediateSteps()` function is a natural fit — just update the steps array progressively
  - The "Thinking..." spinner (`Loader2` icon) should be replaced with real-time thought display as events arrive
  - Add a "typewriter" effect for the final answer text

- **File:** `frontend/src/App.css` (MODIFY)
  - Add CSS animation for streaming text appearance:
    ```css
    .streaming-text { animation: fadeIn 0.3s ease-in; }
    .thought-streaming { border-left: 3px solid #6366f1; animation: slideIn 0.2s ease-out; }
    ```

---

## Verification Plan

### Conversation Memory
1. Login → send "Show total sales for 2023" → receive result
2. Follow up with "Now break that down by region" → verify the agent understands "that" refers to 2023 sales
3. Follow up with "Filter to just North" → verify it narrows the previous result
4. Click "New Conversation" → ask "Filter to just South" → verify it doesn't understand (no prior context)
5. Verify that after 30 minutes of inactivity, the session is cleaned up

### Streaming
1. Send a complex query → verify that thinking steps appear progressively (not all at once)
2. Verify the final answer appears with a typewriter effect
3. Verify SSE connection closes properly after the response
4. Test the non-streaming `/api/chat` endpoint still works (backward compatibility)
5. Test error handling: if the agent fails mid-stream, verify the error is communicated via SSE
