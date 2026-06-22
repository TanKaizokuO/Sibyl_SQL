# Phase 4 — Geographic Visualization & Model Flexibility

> **Items covered:** #10 (Choropleth/Map Visualization), #8 (Model Abstraction Note)
> **Rationale:** The choropleth map is a natural extension of Phase 3's visualization improvements — it adds a new chart type (`choropleth`) that the LLM can now suggest. Item #8 (model note) is a lightweight config/documentation change that pairs naturally since we're already touching the LLM configuration layer.

---

## 4.1 Choropleth / Map Visualization (Item #10)

### Problem
The project has regional data with a `region` column in `sales_data`, and the `AutoChartLogic.ts` already detects geographic columns (`isGeographicColumn()` at line 175). However, it defaults to a bar chart for regional data. A choropleth/map visualization would be a much stronger visual demo, especially since the data has North/South/East/West regions.

### Changes Required

#### Frontend Layer

- **File:** `frontend/package.json` (MODIFY)
  - Add dependency: `"react-simple-maps": "^3.0.0"` (lightweight, works alongside recharts)
  - Run `npm install` after modification

- **File:** `frontend/src/components/ChoroplethMap.tsx` (NEW)
  - A React component that renders an India or US region map (depending on the data)
  - Props:
    - `data: Array<{ region: string, value: number }>` — the data to visualize
    - `valueKey: string` — which numeric column to use for coloring
    - `regionKey: string` — which column contains region names
    - `title?: string` — chart title
  - Implementation:
    - Use `react-simple-maps` with `ComposableMap`, `Geographies`, `Geography`
    - Color scale: Use a sequential color palette (e.g., light blue → deep indigo) based on the value
    - Tooltip on hover: show region name + value
    - Legend: gradient bar showing min-max range
    - Support two modes:
      1. **India states mode:** When region values match Indian state names (detect by checking if values include "Maharashtra", "Tamil Nadu", etc.)
      2. **Cardinal directions mode:** When region values are "North", "South", "East", "West" — render a simplified 4-quadrant map with labeled sections
      3. **US states mode:** When region values match US state names
    - Fallback: If regions don't match any geography, render a horizontal bar chart with a map icon badge
  - GeoJSON source: Use the free TopoJSON files bundled with `react-simple-maps`:
    - World: `https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json`
    - For India/US specific, bundle small TopoJSON files in `frontend/src/assets/geo/`

- **File:** `frontend/src/utils/AutoChartLogic.ts` (MODIFY)
  - Add `'choropleth'` to the `ChartRecommendation.chartType` union type
  - Modify **RULE 4** (Geographic/Regional Data, line 308-325):
    - Change `chartType: 'bar'` to `chartType: 'choropleth'`
    - Update reasoning: `"🗺️ Auto-detected: Geographic/regional data - showing choropleth map"`
  - Update `determineChartTypeWithHint` to accept `'choropleth'` from LLM hints

- **File:** `frontend/src/components/DataVisualizerEnhanced.tsx` (MODIFY)
  - Import `ChoroplethMap`
  - Add a `case 'choropleth':` to the chart type switch/conditional:
    ```tsx
    {recommendation.chartType === 'choropleth' && (
      <ChoroplethMap 
        data={data}
        regionKey={recommendation.metadata.suggestedXAxis}
        valueKey={recommendation.metadata.suggestedYAxis[0]}
      />
    )}
    ```

- **File:** `frontend/src/components/DataVisualizer.css` (MODIFY)
  - Add styles for the choropleth container:
    ```css
    .choropleth-container {
      width: 100%;
      max-width: 800px;
      margin: 0 auto;
      padding: 16px;
    }
    .choropleth-tooltip {
      background: rgba(15, 23, 42, 0.95);
      border: 1px solid rgba(99, 102, 241, 0.3);
      border-radius: 8px;
      padding: 8px 12px;
      font-size: 0.85rem;
      color: #e2e8f0;
      pointer-events: none;
    }
    .choropleth-legend {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      margin-top: 12px;
      font-size: 0.8rem;
      color: #94a3b8;
    }
    .choropleth-gradient {
      width: 200px;
      height: 12px;
      border-radius: 6px;
      background: linear-gradient(to right, #dbeafe, #3b82f6, #1e3a5f);
    }
    ```

---

## 4.2 Model Abstraction & Provider Note (Item #8)

### Problem
The project config defaults to Ollama with `llama3.1:8b` locally (`config.py:48-52`), but the report claims "production-ready." The model choice should be clearly documented as configurable, and the codebase should make swapping trivial.

### Changes Required

- **File:** `backend/app/core/config.py` (MODIFY)
  - Add a clear docstring block above the LLM Configuration section:
    ```python
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
    #
    # To switch providers, change LLM_PROVIDER and LLM_MODEL in .env:
    #   LLM_PROVIDER=gemini
    #   LLM_MODEL=gemini-2.0-flash
    # ================================
    ```
  - Add `openai_api_key: str = Field(default="", env="OPENAI_API_KEY")` for future support

- **File:** `backend/app/agent/cognitive_agent.py` (MODIFY)
  - Add an `elif settings.llm_provider == "openai"` branch in the LLM initialization:
    ```python
    elif settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
    ```
  - Add a final `else: raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")` branch

- **File:** `.env.example` (MODIFY)
  - Add clear comments showing how to switch providers:
    ```
    # LLM Provider: "ollama" (local/free), "gemini" (Google API), "openai" (OpenAI API)
    LLM_PROVIDER=ollama
    LLM_MODEL=llama3.1:8b
    
    # For Gemini (uncomment and set):
    # LLM_PROVIDER=gemini
    # LLM_MODEL=gemini-2.0-flash
    # GOOGLE_API_KEY=your_key_here
    
    # For OpenAI (uncomment and set):
    # LLM_PROVIDER=openai
    # LLM_MODEL=gpt-4o-mini
    # OPENAI_API_KEY=your_key_here
    ```

- **File:** `README.md` (MODIFY)
  - Add a "Model Configuration" section explaining the tradeoffs:
    - Development: Ollama with local models (free, private, slower)
    - Production: Gemini or OpenAI (fast, accurate, API costs)
    - One-line switch via environment variable

---

## Verification Plan

### Choropleth Map
1. Login as admin → ask "show total sales by region" → verify a choropleth/map renders instead of a bar chart
2. Verify the map correctly colors regions based on sales values
3. Verify hover tooltips show region name + value
4. Verify the legend gradient renders correctly
5. If the LLM suggests `choropleth` via `[VIZ_HINT]`, verify it's used; if not, verify the heuristic (Rule 4) triggers it
6. Test with non-geographic data → verify it does NOT show a map (falls back to bar/other)

### Model Flexibility
1. Verify `.env.example` documents all three providers clearly
2. Test with `LLM_PROVIDER=ollama` → verify it works as before
3. If you have a Gemini API key: set `LLM_PROVIDER=gemini` and `LLM_MODEL=gemini-2.0-flash` → verify the agent works with Gemini
4. Verify that an invalid `LLM_PROVIDER` value raises a clear error at startup
