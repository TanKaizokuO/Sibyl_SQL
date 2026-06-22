# Phase 3 — Intelligent Visualization & LLM-Driven Chart Selection

> **Items covered:** #6 (LLM-Based Chart Detection), #7 (Schema-Aware Query Suggestions)
> **Rationale:** These two items form the "smart UX" vertical. Replacing brittle heuristic chart detection with LLM-driven analysis makes visualization semantically aware, and adding follow-up suggestions transforms the UI from reactive to proactive. Both leverage the LLM that's already in the loop.

---

## 3.1 LLM-Based Chart Type Detection (Item #6)

### Problem
The current `AutoChartLogic.ts` (`frontend/src/utils/AutoChartLogic.ts`, 546 lines) uses 11 heuristic rules to determine chart types. While impressive, it's inherently brittle — it can't understand semantic context. For example, a query like "show quarterly trends" implies a time series, but if the LLM returns columns named `q1, q2, q3, q4` (not `quarter`), the heuristic misses the temporal pattern. The LLM already has semantic context about what the user asked and what the data means.

### Changes Required

#### Backend Layer

- **File:** `backend/app/agent/cognitive_agent.py` (MODIFY)
  - Modify the `AGENT_PROMPT_TEMPLATE` to instruct the agent to include visualization metadata in its final answer:
    ```
    VISUALIZATION GUIDANCE:
    When your query returns tabular data, include a visualization hint in your Final Answer using this format:
    
    [VIZ_HINT]
    chart_type: <bar|line|area|pie|table|choropleth>
    x_axis: <column_name for x-axis>
    y_axis: <comma-separated column names for y-axis>
    reasoning: <one-line explanation of why this chart type fits>
    [/VIZ_HINT]
    
    Choose chart_type based on the SEMANTIC MEANING of the query:
    - "trends", "over time", "growth" → line or area
    - "distribution", "breakdown", "share" → pie (if ≤8 categories)
    - "compare", "versus", "by region" → bar
    - "geographic", "map", "by state/country" → choropleth (if regional data)
    - Large datasets (50+ rows) or complex structure → table
    ```

  - Modify the response processing in `CognitiveAgent.run()` to parse the `[VIZ_HINT]...[/VIZ_HINT]` block from the agent's output:
    - Extract `chart_type`, `x_axis`, `y_axis`, `reasoning` into a `visualization_hint` dict
    - Strip the `[VIZ_HINT]` block from the displayed response text
    - Add `visualization_hint` to the response dict alongside `response`, `intermediate_steps`, etc.

- **File:** `backend/app/api/routes/agent.py` (MODIFY)
  - Add `visualization_hint: Optional[Dict]` to the `ChatResponse` model
  - Pass through the `visualization_hint` from the agent's response

#### Frontend Layer

- **File:** `frontend/src/utils/AutoChartLogic.ts` (MODIFY)
  - **Do NOT delete** — keep as fallback
  - Add a new exported function:
    ```typescript
    export function determineChartTypeWithHint(
      data: any[], 
      llmHint: { chart_type: string; x_axis: string; y_axis: string; reasoning: string } | null
    ): ChartRecommendation
    ```
  - Logic:
    1. If `llmHint` is provided and `llmHint.chart_type` is a valid type → use it, set confidence to 98, prepend `"🤖 AI-suggested: "` to the reasoning
    2. If `llmHint` is null or invalid → fall back to existing `determineChartType(data)` heuristic
  - This gives the LLM's semantic understanding priority while keeping the heuristic as a safety net

- **File:** `frontend/src/components/DataVisualizerEnhanced.tsx` (MODIFY)
  - Accept a new optional prop: `llmVisualizationHint`
  - Pass it to `determineChartTypeWithHint()` instead of `determineChartType()`
  - Display the reasoning text (whether LLM or heuristic) in a small badge/tooltip near the chart

- **File:** `frontend/src/App.jsx` (MODIFY)
  - Extract `visualization_hint` from the API response
  - Pass it as a prop to `DataVisualizerEnhanced`:
    ```jsx
    <DataVisualizerEnhanced 
      stepData={visualizationData} 
      llmVisualizationHint={msg.visualizationHint} 
    />
    ```
  - Store `visualizationHint` in the message state alongside `intermediateSteps`

---

## 3.2 Schema-Aware Query Suggestions (Item #7)

### Problem
After each response, non-technical users often don't know what to ask next. The system has rich schema knowledge via RAG but doesn't proactively suggest follow-up questions. This is a missed opportunity to guide exploration.

### Changes Required

#### Backend Layer

- **File:** `backend/app/agent/suggestion_engine.py` (NEW)
  - Function `generate_follow_up_suggestions(user_query: str, agent_response: str, role: str, region: str | None) -> List[Dict[str, str]]`:
    - Uses the RAG retriever to get the schema context relevant to the current query
    - Calls the LLM with a focused prompt:
      ```
      Based on the user's query "{user_query}" and the database schema context below, 
      suggest 3 follow-up questions the user might want to ask next.
      
      Rules:
      - Questions should be natural language, not SQL
      - Questions should build on the current query (drill down, compare, trend, filter)
      - Questions should be feasible given the schema
      - Format as JSON array: [{"question": "...", "category": "drill-down|compare|trend|filter"}]
      
      Schema context:
      {schema_context}
      
      Current query: {user_query}
      Current result summary: {result_summary}
      ```
    - Returns 2-3 suggestions as `[{"question": "...", "category": "..."}]`
    - Uses a lightweight LLM call (low `max_tokens`, high `temperature` for variety)

- **File:** `backend/app/agent/cognitive_agent.py` (MODIFY)
  - After `agent_executor.invoke()` completes, call `generate_follow_up_suggestions()` with the query and response
  - Add `suggestions` to the response dict

- **File:** `backend/app/api/routes/agent.py` (MODIFY)
  - Add `suggestions: Optional[List[Dict]]` to the `ChatResponse` model
  - Pass through the suggestions from the agent

#### Frontend Layer

- **File:** `frontend/src/components/SuggestionChips.jsx` (NEW)
  - A component that renders 2-3 clickable suggestion chips below the assistant's response
  - Props: `suggestions: Array<{question: string, category: string}>`, `onSuggestionClick: (question: string) => void`
  - Styling:
    - Horizontal row of rounded pills/chips
    - Each chip has a small icon based on category:
      - `drill-down` → 🔍
      - `compare` → ⚖️
      - `trend` → 📈
      - `filter` → 🎯
    - Hover effect: subtle scale + color shift
    - Click sends the suggestion text as the next user message

- **File:** `frontend/src/App.jsx` (MODIFY)
  - Store `suggestions` in the message state
  - Render `SuggestionChips` below each assistant message that has suggestions
  - When a suggestion chip is clicked, set it as the input value and trigger `handleSubmit`

- **File:** `frontend/src/App.css` or `frontend/src/components/SuggestionChips.css` (NEW)
  - Styles for suggestion chips:
    ```css
    .suggestion-chips {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px solid rgba(255,255,255,0.1);
    }
    .suggestion-chip {
      padding: 6px 14px;
      border-radius: 20px;
      background: rgba(99, 102, 241, 0.15);
      border: 1px solid rgba(99, 102, 241, 0.3);
      color: #a5b4fc;
      font-size: 0.85rem;
      cursor: pointer;
      transition: all 0.2s ease;
    }
    .suggestion-chip:hover {
      background: rgba(99, 102, 241, 0.3);
      transform: scale(1.03);
    }
    ```

---

## Verification Plan

### LLM Chart Detection
1. Ask "show quarterly sales trends for 2023" → verify the LLM suggests `line` chart (not dependent on column naming)
2. Ask "what's the sales distribution by region" → verify `pie` chart is suggested
3. Ask "compare North vs South sales" → verify `bar` chart is suggested
4. Ask a complex query with 50+ rows → verify `table` is suggested
5. Verify the heuristic fallback works: modify the agent to not return `[VIZ_HINT]` → verify the old heuristic still picks a reasonable chart

### Query Suggestions
1. Ask "show total sales for 2023" → verify 2-3 follow-up suggestions appear (e.g., "Break down by region", "Compare with 2022", "Show quarterly trend")
2. Click a suggestion chip → verify it's sent as the next query
3. Verify suggestions are contextually relevant (not generic)
4. Verify the suggestions respect the user's role (don't suggest mutations for viewers)
