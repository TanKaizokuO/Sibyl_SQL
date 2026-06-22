/**
 * Cognitive Database Agent - Intelligent Chart Type Detection
 * ==========================================================
 *
 * This module implements a sophisticated heuristic-based engine that automatically
 * determines the optimal chart type for visualizing database query results.
 *
 * THEORY: Heuristic-Based Data Analysis
 * -------------------------------------
 * Instead of forcing users to manually select chart types, we apply data science
 * principles to analyze the structure, cardinality, and semantic meaning of data
 * to automatically suggest the most effective visualization.
 *
 * Key Principles:
 * 1. **Temporal Data** → Line/Area charts (show trends over time)
 * 2. **Part-to-Whole** → Pie charts (show proportions)
 * 3. **Categorical Comparison** → Bar charts (compare discrete values)
 * 4. **High Cardinality** → Table view (too many categories for charts)
 * 5. **Geographic** → Bar charts with regional emphasis
 *
 * @module AutoChartLogic
 */

export interface DataColumn {
  name: string;
  type: 'numeric' | 'categorical' | 'temporal' | 'text';
  cardinality: number;
  sampleValues: any[];
}

export interface ChartRecommendation {
  chartType: 'bar' | 'line' | 'area' | 'pie' | 'table' | 'choropleth';
  confidence: number; // 0-100
  reasoning: string;
  metadata: {
    rowCount: number;
    categoryCardinality: number;
    numericColumns: number;
    hasTimeDimension: boolean;
    hasGeographicDimension: boolean;
    isPartToWhole: boolean;
    suggestedXAxis: string | null;
    suggestedYAxis: string[];
  };
}

export interface DataAnalysis {
  columns: DataColumn[];
  rowCount: number;
  numericKeys: string[];
  categoryKeys: string[];
  timeKeys: string[];
  geoKeys: string[];
}

/**
 * Main function: Determines the optimal chart type for given data
 *
 * @param data - Array of data objects from database query
 * @returns Chart recommendation with reasoning
 */
export function determineChartType(data: any[]): ChartRecommendation {
  // Validation
  if (!data || !Array.isArray(data) || data.length === 0) {
    return {
      chartType: 'table',
      confidence: 100,
      reasoning: 'No data available to visualize',
      metadata: {
        rowCount: 0,
        categoryCardinality: 0,
        numericColumns: 0,
        hasTimeDimension: false,
        hasGeographicDimension: false,
        isPartToWhole: false,
        suggestedXAxis: null,
        suggestedYAxis: [],
      },
    };
  }

  // Analyze data structure
  const analysis = analyzeDataStructure(data);

  // Apply heuristic rules (10+ rules as requested)
  const recommendation = applyHeuristicRules(analysis, data);

  return recommendation;
}

/**
 * Analyzes the structure of the data to understand its characteristics
 */
function analyzeDataStructure(data: any[]): DataAnalysis {
  const sample = data[0];
  const keys = Object.keys(sample);

  const columns: DataColumn[] = keys.map((key) => {
    const values = data.map((row) => row[key]);
    const uniqueValues = new Set(values);

    return {
      name: key,
      type: classifyColumnType(key, values),
      cardinality: uniqueValues.size,
      sampleValues: Array.from(uniqueValues).slice(0, 10),
    };
  });

  // Categorize columns
  const numericKeys = columns
    .filter((col) => col.type === 'numeric')
    .map((col) => col.name);

  const categoryKeys = columns
    .filter((col) => col.type === 'categorical')
    .map((col) => col.name);

  const timeKeys = columns
    .filter((col) => col.type === 'temporal')
    .map((col) => col.name);

  const geoKeys = columns
    .filter((col) => isGeographicColumn(col.name))
    .map((col) => col.name);

  return {
    columns,
    rowCount: data.length,
    numericKeys,
    categoryKeys,
    timeKeys,
    geoKeys,
  };
}

/**
 * Classifies a column type based on its name and values
 */
function classifyColumnType(
  columnName: string,
  values: any[]
): 'numeric' | 'categorical' | 'temporal' | 'text' {
  const lowerName = columnName.toLowerCase();

  // Check for temporal indicators
  if (
    ['year', 'month', 'quarter', 'day', 'date', 'time', 'datetime', 'timestamp'].some((t) =>
      lowerName.includes(t)
    )
  ) {
    return 'temporal';
  }

  // Check for numeric values
  const numericCount = values.filter((v) => !isNaN(parseFloat(v)) && v !== null).length;
  const numericRatio = numericCount / values.length;

  if (numericRatio > 0.8) {
    return 'numeric';
  }

  // Check for categorical (low cardinality text)
  const uniqueValues = new Set(values);
  if (uniqueValues.size < values.length * 0.5 && uniqueValues.size < 50) {
    return 'categorical';
  }

  return 'text';
}

/**
 * Checks if a column name suggests geographic data
 */
function isGeographicColumn(columnName: string): boolean {
  const lowerName = columnName.toLowerCase();
  const geoKeywords = [
    'region',
    'country',
    'state',
    'city',
    'location',
    'territory',
    'area',
    'zone',
    'district',
    'province',
  ];

  return geoKeywords.some((keyword) => lowerName.includes(keyword));
}

/**
 * Applies 10+ heuristic rules to determine the best chart type
 */
function applyHeuristicRules(analysis: DataAnalysis, data: any[]): ChartRecommendation {
  const {
    rowCount,
    numericKeys,
    categoryKeys,
    timeKeys,
    geoKeys,
    columns,
  } = analysis;

  // Calculate aggregate metrics
  const hasTimeDimension = timeKeys.length > 0;
  const hasGeographicDimension = geoKeys.length > 0;
  const categoryCardinality = categoryKeys.length > 0
    ? columns.find((col) => col.name === categoryKeys[0])?.cardinality || 0
    : 0;

  // ============================================================================
  // RULE 1: Time Series Detection (HIGHEST PRIORITY)
  // ============================================================================
  // Rationale: Temporal data is best shown as trends (line/area charts)
  if (hasTimeDimension && numericKeys.length >= 1) {
    // Sub-rule 1a: Multiple metrics → Area chart for cumulative view
    if (numericKeys.length > 1 && rowCount >= 3) {
      return {
        chartType: 'area',
        confidence: 95,
        reasoning: '📈 Auto-detected: Time series with multiple metrics - showing cumulative trends over time',
        metadata: {
          rowCount,
          categoryCardinality,
          numericColumns: numericKeys.length,
          hasTimeDimension: true,
          hasGeographicDimension,
          isPartToWhole: false,
          suggestedXAxis: timeKeys[0],
          suggestedYAxis: numericKeys,
        },
      };
    }

    // Sub-rule 1b: Single metric → Line chart for trend clarity
    return {
      chartType: 'line',
      confidence: 95,
      reasoning: '📈 Auto-detected: Time series data with numeric metric - showing trend over time',
      metadata: {
        rowCount,
        categoryCardinality,
        numericColumns: numericKeys.length,
        hasTimeDimension: true,
        hasGeographicDimension,
        isPartToWhole: false,
        suggestedXAxis: timeKeys[0],
        suggestedYAxis: numericKeys,
      },
    };
  }

  // ============================================================================
  // RULE 2: Part-to-Whole Relationship Detection
  // ============================================================================
  // Rationale: Proportional data is best shown as pie charts
  const isPartToWhole = detectPartToWhole(data, numericKeys, categoryKeys);
  if (isPartToWhole && categoryCardinality <= 8) {
    return {
      chartType: 'pie',
      confidence: 90,
      reasoning: '🥧 Auto-detected: Part-to-whole relationship with proportional data - showing distribution',
      metadata: {
        rowCount,
        categoryCardinality,
        numericColumns: numericKeys.length,
        hasTimeDimension,
        hasGeographicDimension,
        isPartToWhole: true,
        suggestedXAxis: categoryKeys[0] || null,
        suggestedYAxis: numericKeys,
      },
    };
  }

  // ============================================================================
  // RULE 3: Low Cardinality Categorical (2-8 items)
  // ============================================================================
  // Rationale: Few categories with single metric → Ideal for pie charts
  if (
    categoryCardinality >= 2 &&
    categoryCardinality <= 8 &&
    numericKeys.length === 1 &&
    rowCount === categoryCardinality
  ) {
    return {
      chartType: 'pie',
      confidence: 85,
      reasoning: '🥧 Auto-detected: Low cardinality categorical data (2-8 items) - showing distribution',
      metadata: {
        rowCount,
        categoryCardinality,
        numericColumns: numericKeys.length,
        hasTimeDimension,
        hasGeographicDimension,
        isPartToWhole: false,
        suggestedXAxis: categoryKeys[0] || null,
        suggestedYAxis: numericKeys,
      },
    };
  }

  // ============================================================================
  // RULE 4: Geographic/Regional Data
  // ============================================================================
  // Rationale: Regional comparisons are best shown as choropleth map
  if (hasGeographicDimension && numericKeys.length >= 1) {
    return {
      chartType: 'choropleth',
      confidence: 90,
      reasoning: '🗺️ Auto-detected: Geographic/regional data - showing choropleth map',
      metadata: {
        rowCount,
        categoryCardinality,
        numericColumns: numericKeys.length,
        hasTimeDimension,
        hasGeographicDimension: true,
        isPartToWhole: false,
        suggestedXAxis: geoKeys[0],
        suggestedYAxis: numericKeys,
      },
    };
  }

  // ============================================================================
  // RULE 5: Medium Cardinality Categorical (9-20 items)
  // ============================================================================
  // Rationale: Medium number of categories → Bar chart for easy comparison
  if (categoryCardinality >= 9 && categoryCardinality <= 20 && numericKeys.length >= 1) {
    return {
      chartType: 'bar',
      confidence: 85,
      reasoning: '📊 Auto-detected: Medium cardinality categorical data (9-20 items) - bar chart for comparison',
      metadata: {
        rowCount,
        categoryCardinality,
        numericColumns: numericKeys.length,
        hasTimeDimension,
        hasGeographicDimension,
        isPartToWhole: false,
        suggestedXAxis: categoryKeys[0] || null,
        suggestedYAxis: numericKeys,
      },
    };
  }

  // ============================================================================
  // RULE 6: High Cardinality Categorical (21-50 items)
  // ============================================================================
  // Rationale: Many categories → Bar chart (still readable) or aggregate
  if (categoryCardinality >= 21 && categoryCardinality <= 50 && numericKeys.length >= 1) {
    return {
      chartType: 'bar',
      confidence: 70,
      reasoning: '📊 Auto-detected: High cardinality data (21-50 items) - bar chart with scrollable view',
      metadata: {
        rowCount,
        categoryCardinality,
        numericColumns: numericKeys.length,
        hasTimeDimension,
        hasGeographicDimension,
        isPartToWhole: false,
        suggestedXAxis: categoryKeys[0] || null,
        suggestedYAxis: numericKeys,
      },
    };
  }

  // ============================================================================
  // RULE 7: Very High Cardinality (50+ items)
  // ============================================================================
  // Rationale: Too many categories → Table is more effective than charts
  if (categoryCardinality > 50 || rowCount > 100) {
    return {
      chartType: 'table',
      confidence: 95,
      reasoning: '📋 Auto-detected: Very high cardinality (50+ categories) - table view recommended for detailed data',
      metadata: {
        rowCount,
        categoryCardinality,
        numericColumns: numericKeys.length,
        hasTimeDimension,
        hasGeographicDimension,
        isPartToWhole: false,
        suggestedXAxis: null,
        suggestedYAxis: numericKeys,
      },
    };
  }

  // ============================================================================
  // RULE 8: Multiple Metrics, No Categories
  // ============================================================================
  // Rationale: Correlation/comparison of multiple metrics → Line chart
  if (numericKeys.length > 1 && categoryKeys.length === 0 && rowCount > 1) {
    return {
      chartType: 'line',
      confidence: 80,
      reasoning: '📈 Auto-detected: Multiple numeric metrics - showing comparative trends',
      metadata: {
        rowCount,
        categoryCardinality: 0,
        numericColumns: numericKeys.length,
        hasTimeDimension,
        hasGeographicDimension,
        isPartToWhole: false,
        suggestedXAxis: 'index',
        suggestedYAxis: numericKeys,
      },
    };
  }

  // ============================================================================
  // RULE 9: Large Dataset with Aggregation Potential
  // ============================================================================
  // Rationale: Large datasets (>100 rows) → Show aggregated bar view
  if (rowCount > 100 && categoryKeys.length >= 1 && numericKeys.length >= 1) {
    return {
      chartType: 'bar',
      confidence: 75,
      reasoning: '📊 Auto-detected: Large dataset (100+ rows) - showing aggregated bar chart view',
      metadata: {
        rowCount,
        categoryCardinality,
        numericColumns: numericKeys.length,
        hasTimeDimension,
        hasGeographicDimension,
        isPartToWhole: false,
        suggestedXAxis: categoryKeys[0],
        suggestedYAxis: numericKeys,
      },
    };
  }

  // ============================================================================
  // RULE 10: Simple Categorical with Metrics
  // ============================================================================
  // Rationale: Basic categorical data → Default to bar chart for comparisons
  if (categoryKeys.length >= 1 && numericKeys.length >= 1) {
    return {
      chartType: 'bar',
      confidence: 80,
      reasoning: '📊 Auto-detected: Categorical data with numeric metrics - bar chart for comparison',
      metadata: {
        rowCount,
        categoryCardinality,
        numericColumns: numericKeys.length,
        hasTimeDimension,
        hasGeographicDimension,
        isPartToWhole: false,
        suggestedXAxis: categoryKeys[0],
        suggestedYAxis: numericKeys,
      },
    };
  }

  // ============================================================================
  // RULE 11 (FALLBACK): Complex/Unknown Structure
  // ============================================================================
  // Rationale: When structure is unclear → Default to table for raw data view
  return {
    chartType: 'table',
    confidence: 60,
    reasoning: '📋 Auto-detected: Complex or mixed data types - table view for comprehensive display',
    metadata: {
      rowCount,
      categoryCardinality,
      numericColumns: numericKeys.length,
      hasTimeDimension,
      hasGeographicDimension,
      isPartToWhole: false,
      suggestedXAxis: null,
      suggestedYAxis: numericKeys,
    },
  };
}

/**
 * Detects if data represents a part-to-whole relationship
 * (e.g., values that sum to 100% or represent proportional distribution)
 */
function detectPartToWhole(
  data: any[],
  numericKeys: string[],
  categoryKeys: string[]
): boolean {
  // Must have exactly 1 numeric metric and 1 category
  if (numericKeys.length !== 1 || categoryKeys.length !== 1) {
    return false;
  }

  // Must have between 2-12 data points (reasonable for pie chart)
  if (data.length < 2 || data.length > 12) {
    return false;
  }

  // Check if values sum to a meaningful total (not just random numbers)
  const numericKey = numericKeys[0];
  const total = data.reduce((sum, row) => sum + (parseFloat(row[numericKey]) || 0), 0);

  // Consider it part-to-whole if:
  // 1. Total is close to 100 (percentage data)
  // 2. Total is positive and meaningful (proportional data)
  // 3. No negative values (proportions are positive)
  const hasNegatives = data.some((row) => parseFloat(row[numericKey]) < 0);

  return !hasNegatives && total > 0;
}

/**
 * Utility: Get human-readable explanation of the chart choice
 */
export function explainChartChoice(recommendation: ChartRecommendation): string {
  const { metadata } = recommendation;

  let explanation = recommendation.reasoning + '\n\n';
  explanation += `Data characteristics:\n`;
  explanation += `• ${metadata.rowCount} data points\n`;
  explanation += `• ${metadata.numericColumns} numeric column(s)\n`;
  explanation += `• ${metadata.categoryCardinality} unique categories\n`;

  if (metadata.hasTimeDimension) {
    explanation += `• ⏰ Contains time dimension (year/month/quarter)\n`;
  }

  if (metadata.hasGeographicDimension) {
    explanation += `• 🌍 Contains geographic dimension (region/country/city)\n`;
  }

  if (metadata.isPartToWhole) {
    explanation += `• 🥧 Represents part-to-whole relationship\n`;
  }

  return explanation;
}


/**
 * LLM Visualization Hint interface
 * Matches the dict returned by the backend _parse_viz_hint() function.
 */
export interface LLMVisualizationHint {
  chart_type: string;
  x_axis: string;
  y_axis: string;
  reasoning: string;
}

/**
 * LLM-first chart type determination with heuristic fallback.
 *
 * THEORY: LLM Semantic Priority
 * -----------------------------
 * The LLM understands the *intent* of the query — "show quarterly trends" implies
 * a time series even if columns are named q1, q2, q3, q4 (not 'quarter').
 * Heuristics are structural and can miss semantic context.
 *
 * Strategy:
 * 1. If a valid llmHint is provided → use it at 98% confidence
 *    (prepend 🤖 AI-suggested to the reasoning so users know the source)
 * 2. Otherwise fall back to the existing determineChartType() heuristic
 *
 * @param data     - Array of data objects from database query
 * @param llmHint  - Optional hint from the LLM's [VIZ_HINT] block
 * @returns ChartRecommendation
 */
export function determineChartTypeWithHint(
  data: any[],
  llmHint: LLMVisualizationHint | null | undefined
): ChartRecommendation {
  // Always compute heuristic recommendation first (for metadata/axis fallbacks)
  const heuristicRec = determineChartType(data);

  // Guard: no hint or empty data → pure heuristic
  if (!llmHint || !data || data.length === 0) {
    return heuristicRec;
  }

  // Validate chart_type from LLM
  const validChartTypes: ChartRecommendation['chartType'][] = [
    'bar', 'line', 'area', 'pie', 'table', 'choropleth',
  ];
  const rawChartType = llmHint.chart_type?.toLowerCase?.() ?? '';
  const llmChartType = validChartTypes.find((t) => t === rawChartType);

  // If the LLM returned an unsupported/empty chart type → fall back to heuristic
  if (!llmChartType) {
    return heuristicRec;
  }

  // Parse y_axis from comma-separated string
  const llmYAxis = llmHint.y_axis
    ? llmHint.y_axis.split(',').map((s) => s.trim()).filter(Boolean)
    : heuristicRec.metadata.suggestedYAxis;

  // Use LLM x_axis if provided; fall back to heuristic
  const llmXAxis =
    llmHint.x_axis?.trim() || heuristicRec.metadata.suggestedXAxis;

  return {
    chartType: llmChartType,
    confidence: 98, // High confidence — semantic understanding
    reasoning: `🤖 AI-suggested: ${llmHint.reasoning || `${llmChartType} chart`}`,
    metadata: {
      // Carry structural metadata from heuristic (it still analyzed the data)
      ...heuristicRec.metadata,
      suggestedXAxis: llmXAxis,
      suggestedYAxis:
        llmYAxis.length > 0 ? llmYAxis : heuristicRec.metadata.suggestedYAxis,
    },
  };
}


/**
 * Export all public functions and types
 */
export default {
  determineChartType,
  determineChartTypeWithHint,
  explainChartChoice,
};
