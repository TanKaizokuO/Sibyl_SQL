import { useState } from 'react'
import { BarChart, Bar, LineChart, Line, AreaChart, Area, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { BarChart3, LineChart as LineChartIcon, PieChart as PieChartIcon, Table as TableIcon, TrendingUp } from 'lucide-react'

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']

const DataVisualizer = ({ data, stepData }) => {
  const [viewMode, setViewMode] = useState('auto') // 'auto', 'table', 'bar', 'line', 'area', 'pie'

  // Extract data from observations
  const extractedData = data || stepData

  console.log('DataVisualizer received:', { data, stepData, extractedData })

  if (!extractedData || !Array.isArray(extractedData) || extractedData.length === 0) {
    console.log('DataVisualizer: No valid data, returning null')
    return null
  }

  console.log('DataVisualizer: Rendering with', extractedData.length, 'rows')

  // Enhanced data analysis with intelligent chart detection
  const analyzeData = () => {
    const sample = extractedData[0]
    const keys = Object.keys(sample)

    // Find numeric and non-numeric columns
    const numericKeys = keys.filter(key => {
      const value = sample[key]
      return !isNaN(parseFloat(value)) && value !== null
    })

    const categoryKeys = keys.filter(key => !numericKeys.includes(key))

    // Detect time series (has year, month, date, quarter, etc.)
    const hasTimeDimension = keys.some(key =>
      ['year', 'month', 'date', 'quarter', 'day', 'time', 'timestamp', 'datetime'].includes(key.toLowerCase())
    )

    // Detect geographic/regional data
    const hasRegion = keys.some(key =>
      ['region', 'country', 'state', 'city', 'location', 'territory', 'area'].includes(key.toLowerCase())
    )

    // Calculate cardinality (unique values) for category columns
    const getCardinality = (key) => {
      const uniqueValues = new Set(extractedData.map(row => row[key]))
      return uniqueValues.size
    }

    // Get cardinality for first category key
    const categoryCardinality = categoryKeys.length > 0 ? getCardinality(categoryKeys[0]) : 0

    // Detect if data shows part-to-whole relationship (values sum to meaningful total)
    const isPartToWhole = () => {
      if (numericKeys.length === 1 && categoryKeys.length === 1 && extractedData.length <= 12) {
        const total = extractedData.reduce((sum, row) => sum + parseFloat(row[numericKeys[0]] || 0), 0)
        return total > 0 && extractedData.length >= 2 // At least 2 parts
      }
      return false
    }

    // Detect if we have correlation data (multiple numeric columns, no categories)
    const isCorrelationData = numericKeys.length >= 2 && categoryKeys.length === 0

    // Count rows
    const rowCount = extractedData.length

    // **INTELLIGENT CHART TYPE SELECTION**
    let chartType = 'table'
    let reasoning = 'Default view for complex data'

    // Rule 1: Time Series Data (highest priority for temporal analysis)
    if (hasTimeDimension && numericKeys.length >= 1) {
      // Use area chart for time series with multiple metrics (better for cumulative view)
      if (numericKeys.length > 1 && rowCount >= 3) {
        chartType = 'area'
        reasoning = 'Time series with multiple metrics - showing cumulative trends'
      } else {
        chartType = 'line'
        reasoning = 'Time series data detected - showing trends over time'
      }
    }

    // Rule 2: Part-to-Whole Relationship (pie for proportions)
    else if (isPartToWhole()) {
      chartType = 'pie'
      reasoning = 'Part-to-whole relationship - showing proportions'
    }

    // Rule 3: Few Categories with Single Metric (easy comparison)
    else if (categoryCardinality >= 2 && categoryCardinality <= 7 && numericKeys.length === 1) {
      chartType = 'pie'
      reasoning = 'Few categories with single metric - showing distribution'
    }

    // Rule 4: Medium Categories with Metrics (bar for comparison)
    else if (categoryCardinality >= 2 && categoryCardinality <= 20 && numericKeys.length >= 1) {
      chartType = 'bar'
      reasoning = 'Categorical comparison with metrics'
    }

    // Rule 5: Many Categories (bar chart or table for high cardinality)
    else if (categoryCardinality > 20 && categoryCardinality <= 50 && numericKeys.length >= 1) {
      chartType = 'bar'
      reasoning = 'Many categories - bar chart for comparison'
    }

    // Rule 6: Very High Cardinality (table is better)
    else if (categoryCardinality > 50) {
      chartType = 'table'
      reasoning = 'Too many categories - table view recommended'
    }

    // Rule 7: Regional/Geographic Data (always use bar for regions)
    else if (hasRegion && numericKeys.length >= 1) {
      chartType = 'bar'
      reasoning = 'Geographic/regional comparison'
    }

    // Rule 8: Large Datasets (aggregate view)
    else if (rowCount > 100 && categoryKeys.length >= 1 && numericKeys.length >= 1) {
      chartType = 'bar'
      reasoning = 'Large dataset - showing aggregated view'
    }

    // Rule 9: Multiple Metrics, No Categories (line chart for multi-metric trends)
    else if (numericKeys.length > 1 && categoryKeys.length === 0) {
      chartType = 'line'
      reasoning = 'Multiple metrics - showing comparative trends'
    }

    // Rule 10: Simple Categorical Data
    else if (categoryKeys.length >= 1 && numericKeys.length >= 1) {
      chartType = 'bar'
      reasoning = 'Categorical data with metrics'
    }

    console.log('📊 Chart Auto-Detection:', {
      chartType,
      reasoning,
      rowCount,
      categoryCardinality,
      numericKeys: numericKeys.length,
      categoryKeys: categoryKeys.length,
      hasTimeDimension,
      hasRegion
    })

    return {
      chartType,
      categoryKeys,
      numericKeys,
      allKeys: keys,
      hasTimeDimension,
      hasRegion,
      categoryCardinality,
      rowCount,
      reasoning,
      isPartToWhole: isPartToWhole(),
      isCorrelationData
    }
  }

  const analysis = analyzeData()
  const displayMode = viewMode === 'auto' ? analysis.chartType : viewMode

  // Prepare data for charts
  const prepareChartData = () => {
    // Convert numeric strings to numbers
    return extractedData.map(row => {
      const newRow = { ...row }
      analysis.numericKeys.forEach(key => {
        newRow[key] = parseFloat(row[key]) || 0
      })
      return newRow
    })
  }

  const chartData = prepareChartData()

  // Determine X-axis and Y-axis
  const getAxisKeys = () => {
    // For time series, use time dimension as X
    if (analysis.hasTimeDimension) {
      const timeKey = analysis.allKeys.find(key =>
        ['year', 'month', 'date', 'quarter', 'day'].includes(key.toLowerCase())
      )
      return {
        xKey: timeKey,
        yKeys: analysis.numericKeys,
        groupKey: analysis.categoryKeys.find(k => k !== timeKey)
      }
    }

    // For regional/categorical, use category as X
    if (analysis.categoryKeys.length > 0) {
      return {
        xKey: analysis.categoryKeys[0],
        yKeys: analysis.numericKeys,
        groupKey: analysis.categoryKeys[1]
      }
    }

    return {
      xKey: analysis.allKeys[0],
      yKeys: analysis.numericKeys,
      groupKey: null
    }
  }

  const { xKey, yKeys, groupKey } = getAxisKeys()

  // Render different chart types
  const renderChart = () => {
    switch (displayMode) {
      case 'bar':
        return (
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey={xKey} />
              <YAxis />
              <Tooltip />
              <Legend />
              {yKeys.map((key, idx) => (
                <Bar key={key} dataKey={key} fill={COLORS[idx % COLORS.length]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        )

      case 'line':
        return (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey={xKey} />
              <YAxis />
              <Tooltip />
              <Legend />
              {yKeys.map((key, idx) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={COLORS[idx % COLORS.length]}
                  strokeWidth={2}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )

      case 'area':
        return (
          <ResponsiveContainer width="100%" height={400}>
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey={xKey} />
              <YAxis />
              <Tooltip />
              <Legend />
              {yKeys.map((key, idx) => (
                <Area
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={COLORS[idx % COLORS.length]}
                  fill={COLORS[idx % COLORS.length]}
                  fillOpacity={0.6}
                  strokeWidth={2}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        )

      case 'pie':
        const pieData = chartData.map(row => ({
          name: row[xKey],
          value: row[yKeys[0]]
        }))

        return (
          <ResponsiveContainer width="100%" height={400}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={120}
                fill="#8884d8"
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        )

      case 'table':
      default:
        return (
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  {analysis.allKeys.map(key => (
                    <th key={key}>{key}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {extractedData.slice(0, 50).map((row, idx) => (
                  <tr key={idx}>
                    {analysis.allKeys.map(key => (
                      <td key={key}>{row[key]}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {extractedData.length > 50 && (
              <div className="table-footer">
                Showing 50 of {extractedData.length} rows
              </div>
            )}
          </div>
        )
    }
  }

  return (
    <div className="data-visualizer">
      <div className="viz-header">
        <div className="viz-title">
          <BarChart3 className="icon" />
          Data Visualization ({extractedData.length} rows)
        </div>
        <div className="viz-controls">
          <button
            className={`viz-btn ${viewMode === 'auto' ? 'active' : ''}`}
            onClick={() => setViewMode('auto')}
            title="Auto-detect best chart"
          >
            Auto
          </button>
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
        </div>
      </div>

      <div className="viz-content">
        {renderChart()}
      </div>

      <div className="viz-info">
        <span className="viz-badge">Chart: {displayMode}</span>
        {viewMode === 'auto' && analysis.reasoning && (
          <span className="viz-badge viz-badge-reason" title={analysis.reasoning}>
            ℹ️ {analysis.reasoning}
          </span>
        )}
        {analysis.hasTimeDimension && <span className="viz-badge">Time Series</span>}
        {analysis.hasRegion && <span className="viz-badge">Geographic</span>}
        <span className="viz-badge">{analysis.categoryCardinality} categories</span>
        <span className="viz-badge">{analysis.numericKeys.length} metric(s)</span>
        <span className="viz-badge">{analysis.rowCount} rows</span>
      </div>
    </div>
  )
}

export default DataVisualizer
