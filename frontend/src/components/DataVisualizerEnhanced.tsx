/**
 * Cognitive Database Agent - Enhanced Data Visualizer Component
 * =============================================================
 *
 * This component provides intelligent, auto-detecting data visualization with:
 * - 10+ heuristic rules for chart type selection
 * - Visual reasoning badges explaining chart choices
 * - Manual override capability for user preference
 * - Comprehensive metadata display
 *
 * @component DataVisualizerEnhanced
 */

import { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import {
  BarChart3,
  LineChart as LineChartIcon,
  PieChart as PieChartIcon,
  Table as TableIcon,
  TrendingUp,
  Info,
  Sparkles,
  Map as MapIcon,
} from 'lucide-react';
import { determineChartType, determineChartTypeWithHint, ChartRecommendation, LLMVisualizationHint } from '../utils/AutoChartLogic';
import ChoroplethMap from './ChoroplethMap';

// Color palette for charts
const COLORS = [
  '#3b82f6', // Blue
  '#10b981', // Green
  '#f59e0b', // Amber
  '#ef4444', // Red
  '#8b5cf6', // Purple
  '#ec4899', // Pink
  '#14b8a6', // Teal
  '#f97316', // Orange
];

interface DataVisualizerProps {
  data?: any[];
  stepData?: any[];
  /** Optional LLM-generated visualization hint from the [VIZ_HINT] block */
  llmVisualizationHint?: LLMVisualizationHint | null;
}

const DataVisualizerEnhanced: React.FC<DataVisualizerProps> = ({ data, stepData, llmVisualizationHint }) => {
  const [viewMode, setViewMode] = useState<'auto' | 'bar' | 'line' | 'area' | 'pie' | 'table' | 'choropleth'>(
    'auto'
  );
  const [recommendation, setRecommendation] = useState<ChartRecommendation | null>(null);
  const [showMetadata, setShowMetadata] = useState(true);

  // Extract data from props
  const extractedData = data || stepData;

  // Analyze data when it changes — prefer LLM hint when available
  useEffect(() => {
    if (extractedData && Array.isArray(extractedData) && extractedData.length > 0) {
      const rec = determineChartTypeWithHint(extractedData, llmVisualizationHint ?? null);
      setRecommendation(rec);
      const source = llmVisualizationHint ? '🤖 LLM-guided' : '📊 Heuristic';
      console.log(`${source} Chart Detection Result:`, rec);
    }
  }, [extractedData, llmVisualizationHint]);

  // Validation
  if (!extractedData || !Array.isArray(extractedData) || extractedData.length === 0) {
    return null;
  }

  if (!recommendation) {
    return (
      <div className="data-visualizer-loading">
        <Sparkles className="icon-spin" />
        Analyzing data...
      </div>
    );
  }

  // Determine display mode
  const displayMode = viewMode === 'auto' ? recommendation.chartType : viewMode;

  // Prepare chart data (convert numeric strings to numbers)
  const prepareChartData = () => {
    return extractedData.map((row) => {
      const newRow: any = { ...row };
      recommendation.metadata.suggestedYAxis.forEach((key) => {
        if (row[key] !== undefined) {
          newRow[key] = parseFloat(row[key]) || 0;
        }
      });
      return newRow;
    });
  };

  const chartData = prepareChartData();

  // Determine axes
  const xKey = recommendation.metadata.suggestedXAxis || Object.keys(extractedData[0])[0];
  const yKeys = recommendation.metadata.suggestedYAxis;

  // ===========================================================================
  // RENDER FUNCTIONS FOR DIFFERENT CHART TYPES
  // ===========================================================================

  const renderBarChart = () => (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey={xKey} stroke="#6b7280" />
        <YAxis stroke="#6b7280" />
        <Tooltip
          contentStyle={{
            backgroundColor: '#ffffff',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
          }}
        />
        <Legend />
        {yKeys.map((key, idx) => (
          <Bar key={key} dataKey={key} fill={COLORS[idx % COLORS.length]} radius={[4, 4, 0, 0]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );

  const renderLineChart = () => (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey={xKey} stroke="#6b7280" />
        <YAxis stroke="#6b7280" />
        <Tooltip
          contentStyle={{
            backgroundColor: '#ffffff',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
          }}
        />
        <Legend />
        {yKeys.map((key, idx) => (
          <Line
            key={key}
            type="monotone"
            dataKey={key}
            stroke={COLORS[idx % COLORS.length]}
            strokeWidth={2}
            dot={{ fill: COLORS[idx % COLORS.length], r: 4 }}
            activeDot={{ r: 6 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );

  const renderAreaChart = () => (
    <ResponsiveContainer width="100%" height={400}>
      <AreaChart data={chartData}>
        <defs>
          {yKeys.map((key, idx) => (
            <linearGradient key={`gradient-${key}`} id={`color-${key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={COLORS[idx % COLORS.length]} stopOpacity={0.8} />
              <stop offset="95%" stopColor={COLORS[idx % COLORS.length]} stopOpacity={0.1} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey={xKey} stroke="#6b7280" />
        <YAxis stroke="#6b7280" />
        <Tooltip
          contentStyle={{
            backgroundColor: '#ffffff',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
          }}
        />
        <Legend />
        {yKeys.map((key, idx) => (
          <Area
            key={key}
            type="monotone"
            dataKey={key}
            stroke={COLORS[idx % COLORS.length]}
            fillOpacity={1}
            fill={`url(#color-${key})`}
            strokeWidth={2}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );

  const renderPieChart = () => {
    const pieData = chartData.map((row) => ({
      name: row[xKey],
      value: row[yKeys[0]],
    }));

    return (
      <ResponsiveContainer width="100%" height={400}>
        <PieChart>
          <Pie
            data={pieData}
            cx="50%"
            cy="50%"
            labelLine={true}
            label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(1)}%`}
            outerRadius={130}
            fill="#8884d8"
            dataKey="value"
          >
            {pieData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: '#ffffff',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
            }}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    );
  };

  const renderTable = () => {
    const allKeys = Object.keys(extractedData[0]);

    return (
      <div className="data-table-container">
        <div className="data-table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                {allKeys.map((key) => (
                  <th key={key}>{key}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {extractedData.slice(0, 100).map((row, idx) => (
                <tr key={idx}>
                  {allKeys.map((key) => (
                    <td key={key}>{row[key]}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {extractedData.length > 100 && (
          <div className="table-footer">
            <Info className="icon-sm" />
            Showing first 100 of {extractedData.length} rows
          </div>
        )}
      </div>
    );
  };

  // Main chart renderer
  const renderChart = () => {
    switch (displayMode) {
      case 'bar':
        return renderBarChart();
      case 'line':
        return renderLineChart();
      case 'area':
        return renderAreaChart();
      case 'pie':
        return renderPieChart();
      case 'choropleth':
        return (
          <ChoroplethMap
            data={chartData}
            regionKey={recommendation.metadata.suggestedXAxis || ''}
            valueKey={recommendation.metadata.suggestedYAxis[0] || ''}
          />
        );
      case 'table':
      default:
        return renderTable();
    }
  };

  // ===========================================================================
  // MAIN COMPONENT RENDER
  // ===========================================================================

  return (
    <div className="data-visualizer-enhanced">
      {/* Reasoning Badge - shows AI-suggested or heuristic mode */}
      {viewMode === 'auto' && (
        <div className={`viz-reasoning-badge ${llmVisualizationHint ? 'viz-reasoning-badge--ai' : ''}`}>
          <div className="reasoning-badge-content">
            <Sparkles className="icon-badge" />
            <div className="reasoning-text">
              <strong>{llmVisualizationHint ? 'AI Reasoning:' : 'Auto-detected:'}</strong>{' '}
              {recommendation.reasoning}
            </div>
            <div className="confidence-pill">
              {recommendation.confidence}% confidence
            </div>
          </div>
        </div>
      )}

      {/* Header with Controls */}
      <div className="viz-header">
        <div className="viz-title">
          {displayMode === 'area' && <TrendingUp className="icon" />}
          {displayMode === 'bar' && <BarChart3 className="icon" />}
          {displayMode === 'line' && <LineChartIcon className="icon" />}
          {displayMode === 'pie' && <PieChartIcon className="icon" />}
          {displayMode === 'table' && <TableIcon className="icon" />}
          {displayMode === 'choropleth' && <MapIcon className="icon" />}
          <span>
            {displayMode === 'choropleth'
              ? 'Choropleth Map'
              : displayMode.charAt(0).toUpperCase() + displayMode.slice(1) + ' View'}
          </span>
        </div>

        {/* Manual Override Controls */}
        <div className="viz-controls">
          <button
            className={`viz-btn ${viewMode === 'auto' ? 'active' : ''}`}
            onClick={() => setViewMode('auto')}
            title="Auto-detect best chart type"
          >
            <Sparkles className="icon-sm" />
            Auto
          </button>
          <div className="viz-divider"></div>
          <button
            className={`viz-btn ${viewMode === 'table' ? 'active' : ''}`}
            onClick={() => setViewMode('table')}
            title="Table view"
          >
            <TableIcon className="icon-sm" />
          </button>
          <button
            className={`viz-btn ${viewMode === 'bar' ? 'active' : ''}`}
            onClick={() => setViewMode('bar')}
            title="Bar chart"
          >
            <BarChart3 className="icon-sm" />
          </button>
          <button
            className={`viz-btn ${viewMode === 'line' ? 'active' : ''}`}
            onClick={() => setViewMode('line')}
            title="Line chart"
          >
            <LineChartIcon className="icon-sm" />
          </button>
          <button
            className={`viz-btn ${viewMode === 'area' ? 'active' : ''}`}
            onClick={() => setViewMode('area')}
            title="Area chart"
          >
            <TrendingUp className="icon-sm" />
          </button>
          <button
            className={`viz-btn ${viewMode === 'pie' ? 'active' : ''}`}
            onClick={() => setViewMode('pie')}
            title="Pie chart"
          >
            <PieChartIcon className="icon-sm" />
          </button>
          <button
            className={`viz-btn ${viewMode === 'choropleth' ? 'active' : ''}`}
            onClick={() => setViewMode('choropleth')}
            title="Choropleth map"
          >
            <MapIcon className="icon-sm" />
          </button>
        </div>
      </div>

      {/* Chart Content */}
      <div className="viz-content">{renderChart()}</div>

      {/* Info Footer */}
      {showMetadata && (
        <div className="viz-footer">
          <div className="viz-metadata">
            <div className="metadata-item">
              <strong>Row Count:</strong> {recommendation.metadata.rowCount}
            </div>
            <div className="metadata-divider">•</div>
            <div className="metadata-item">
              <strong>Cardinality:</strong> {recommendation.metadata.categoryCardinality}
            </div>
            <div className="metadata-divider">•</div>
            <div className="metadata-item">
              <strong>Metrics:</strong> {recommendation.metadata.numericColumns}
            </div>
            {recommendation.metadata.hasTimeDimension && (
              <>
                <div className="metadata-divider">•</div>
                <div className="metadata-badge">⏰ Time Series</div>
              </>
            )}
            {recommendation.metadata.hasGeographicDimension && (
              <>
                <div className="metadata-divider">•</div>
                <div className="metadata-badge">🌍 Geographic</div>
              </>
            )}
            {recommendation.metadata.isPartToWhole && (
              <>
                <div className="metadata-divider">•</div>
                <div className="metadata-badge">🥧 Part-to-Whole</div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default DataVisualizerEnhanced;
