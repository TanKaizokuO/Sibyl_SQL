/**
 * Cognitive Database Agent - Visualization Test Playground
 * ========================================================
 *
 * Interactive testing component for the intelligent data visualization system.
 * Provides 7 carefully crafted test cases to demonstrate the auto-detection logic.
 *
 * Test Cases:
 * 1. Monthly Sales - Time Series Detection
 * 2. User Roles Distribution - Low Cardinality Pie Chart
 * 3. Product Inventory - High Cardinality Bar Chart
 * 4. Server Logs - Raw Table View
 * 5. Regional Data - Geographic Bar Chart
 * 6. Mixed Numeric - Multi-Metric Line Chart
 * 7. Empty/Error State - Edge Case Handling
 *
 * @component VizTestPlayground
 */

import { useState } from 'react';
import { Beaker, ChevronDown, Copy, Check } from 'lucide-react';
import DataVisualizerEnhanced from './DataVisualizerEnhanced';

// ===========================================================================
// TEST CASE DATA SETS
// ===========================================================================

const TEST_CASES = {
  // Test Case 1: Monthly Sales (Time Series)
  monthly_sales: {
    name: 'Case 1: Monthly Sales (Time Series)',
    description: 'Temporal data with numeric metric. Should auto-detect as LINE or AREA chart.',
    expectedChart: 'Line/Area Chart',
    reasoning: 'Contains month/year columns (time dimension) with sales metric',
    data: [
      { month: 'Jan 2024', sales: 45000, target: 50000 },
      { month: 'Feb 2024', sales: 52000, target: 50000 },
      { month: 'Mar 2024', sales: 61000, target: 55000 },
      { month: 'Apr 2024', sales: 58000, target: 55000 },
      { month: 'May 2024', sales: 71000, target: 60000 },
      { month: 'Jun 2024', sales: 68000, target: 60000 },
      { month: 'Jul 2024', sales: 79000, target: 65000 },
      { month: 'Aug 2024', sales: 83000, target: 65000 },
    ],
  },

  // Test Case 2: User Roles Distribution (Low Cardinality Pie)
  user_roles: {
    name: 'Case 2: User Roles Distribution (Pie/Low Cardinality)',
    description: 'Low cardinality categorical data (2-8 items). Should auto-detect as PIE chart.',
    expectedChart: 'Pie Chart',
    reasoning: 'Small number of categories (5) with proportional values - ideal for pie chart',
    data: [
      { role: 'Admin', count: 5 },
      { role: 'Manager', count: 23 },
      { role: 'Sales Rep', count: 67 },
      { role: 'Analyst', count: 34 },
      { role: 'Viewer', count: 12 },
    ],
  },

  // Test Case 3: Product Inventory (High Cardinality Bar)
  product_inventory: {
    name: 'Case 3: Product Inventory (High Cardinality Bar)',
    description: 'Many categories (15+) with metrics. Should auto-detect as BAR chart.',
    expectedChart: 'Bar Chart',
    reasoning: 'Medium-high cardinality (15 products) - bar chart for easy comparison',
    data: [
      { product: 'Laptop Pro 15"', stock: 45, reorder_point: 20 },
      { product: 'Laptop Air 13"', stock: 67, reorder_point: 30 },
      { product: 'Desktop Tower i7', stock: 23, reorder_point: 15 },
      { product: 'Monitor 27" 4K', stock: 89, reorder_point: 40 },
      { product: 'Monitor 24" FHD', stock: 124, reorder_point: 50 },
      { product: 'Keyboard Mechanical', stock: 156, reorder_point: 60 },
      { product: 'Mouse Wireless', stock: 234, reorder_point: 80 },
      { product: 'Webcam HD', stock: 78, reorder_point: 30 },
      { product: 'Headset Noise-Cancel', stock: 92, reorder_point: 35 },
      { product: 'USB-C Hub 7-port', stock: 145, reorder_point: 50 },
      { product: 'External SSD 1TB', stock: 67, reorder_point: 25 },
      { product: 'RAM DDR4 16GB', stock: 189, reorder_point: 70 },
      { product: 'Graphics Card RTX', stock: 12, reorder_point: 10 },
      { product: 'Power Bank 20000mAh', stock: 201, reorder_point: 75 },
      { product: 'Cable HDMI 2.1', stock: 345, reorder_point: 100 },
    ],
  },

  // Test Case 4: Server Logs (Raw Table)
  server_logs: {
    name: 'Case 4: Server Logs (Raw Table)',
    description: 'Very high cardinality (100+ rows) with mixed types. Should auto-detect as TABLE.',
    expectedChart: 'Table',
    reasoning: 'Too many rows (100+) and complex structure - table view is most readable',
    data: Array.from({ length: 120 }, (_, i) => ({
      timestamp: `2024-11-26 ${String(Math.floor(i / 4)).padStart(2, '0')}:${String((i % 4) * 15).padStart(2, '0')}:00`,
      server_id: `SRV-${String((i % 10) + 1).padStart(3, '0')}`,
      status_code: [200, 200, 200, 304, 404, 500][i % 6],
      response_time_ms: Math.floor(Math.random() * 500) + 50,
      endpoint: ['/api/users', '/api/products', '/api/orders', '/api/auth'][i % 4],
    })),
  },

  // Test Case 5: Regional Data (Geographic)
  regional_sales: {
    name: 'Case 5: Regional Data (Geographic)',
    description: 'Geographic/regional columns. Should auto-detect as BAR chart with regional emphasis.',
    expectedChart: 'Bar Chart',
    reasoning: 'Contains "region" column - geographic comparison best shown as bar chart',
    data: [
      { region: 'North America', revenue: 2450000, customers: 1250 },
      { region: 'South America', revenue: 890000, customers: 480 },
      { region: 'Europe', revenue: 3120000, customers: 1680 },
      { region: 'Asia Pacific', revenue: 4560000, customers: 2340 },
      { region: 'Middle East', revenue: 1230000, customers: 620 },
      { region: 'Africa', revenue: 670000, customers: 380 },
    ],
  },

  // Test Case 6: Mixed Numeric (Multi-Metric Trends)
  performance_metrics: {
    name: 'Case 6: Mixed Numeric (Multi-Metric)',
    description: 'Multiple numeric metrics without categories. Should auto-detect as LINE chart.',
    expectedChart: 'Line Chart',
    reasoning: 'Multiple numeric metrics over time - comparative trend analysis',
    data: [
      { week: 'Week 1', cpu_usage: 45, memory_usage: 62, disk_io: 34, network_throughput: 78 },
      { week: 'Week 2', cpu_usage: 52, memory_usage: 68, disk_io: 41, network_throughput: 82 },
      { week: 'Week 3', cpu_usage: 48, memory_usage: 71, disk_io: 38, network_throughput: 85 },
      { week: 'Week 4', cpu_usage: 61, memory_usage: 75, disk_io: 56, network_throughput: 79 },
      { week: 'Week 5', cpu_usage: 58, memory_usage: 79, disk_io: 52, network_throughput: 91 },
      { week: 'Week 6', cpu_usage: 54, memory_usage: 73, disk_io: 45, network_throughput: 88 },
    ],
  },

  // Test Case 7: Empty/Error State
  empty_data: {
    name: 'Case 7: Empty/Error State',
    description: 'Edge case with no data. Should handle gracefully.',
    expectedChart: 'N/A',
    reasoning: 'No data to visualize - component should handle gracefully',
    data: [],
  },
};

type TestCaseKey = keyof typeof TEST_CASES;

// ===========================================================================
// MAIN COMPONENT
// ===========================================================================

const VizTestPlayground = () => {
  const [selectedCase, setSelectedCase] = useState<TestCaseKey>('monthly_sales');
  const [showDataPreview, setShowDataPreview] = useState(false);
  const [copied, setCopied] = useState(false);

  const currentCase = TEST_CASES[selectedCase];

  // Copy data to clipboard
  const handleCopyData = () => {
    navigator.clipboard.writeText(JSON.stringify(currentCase.data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="viz-test-playground">
      {/* Header */}
      <div className="playground-header">
        <div className="playground-title">
          <Beaker className="icon icon-primary" />
          <h2>Data Visualization Test Playground</h2>
        </div>
        <div className="playground-subtitle">
          Interactive testing of the intelligent chart auto-detection engine
        </div>
      </div>

      {/* Test Case Selector */}
      <div className="test-case-selector">
        <div className="selector-label">
          <strong>Select Test Case:</strong>
        </div>
        <div className="selector-dropdown">
          <select
            className="select-test-case"
            value={selectedCase}
            onChange={(e) => setSelectedCase(e.target.value as TestCaseKey)}
          >
            {Object.entries(TEST_CASES).map(([key, testCase]) => (
              <option key={key} value={key}>
                {testCase.name}
              </option>
            ))}
          </select>
          <ChevronDown className="icon-dropdown" />
        </div>
      </div>

      {/* Test Case Info Card */}
      <div className="test-case-info">
        <div className="info-row">
          <div className="info-label">Description:</div>
          <div className="info-value">{currentCase.description}</div>
        </div>
        <div className="info-row">
          <div className="info-label">Expected Chart:</div>
          <div className="info-value info-value-highlight">{currentCase.expectedChart}</div>
        </div>
        <div className="info-row">
          <div className="info-label">Reasoning:</div>
          <div className="info-value">{currentCase.reasoning}</div>
        </div>
        <div className="info-row">
          <div className="info-label">Data Points:</div>
          <div className="info-value">{currentCase.data.length} rows</div>
        </div>
      </div>

      {/* Data Preview Toggle */}
      <div className="data-preview-controls">
        <button
          className="btn-preview"
          onClick={() => setShowDataPreview(!showDataPreview)}
        >
          {showDataPreview ? '▼ Hide' : '▶ Show'} Raw Data
        </button>
        {showDataPreview && (
          <button className="btn-copy" onClick={handleCopyData}>
            {copied ? (
              <>
                <Check className="icon-sm" /> Copied!
              </>
            ) : (
              <>
                <Copy className="icon-sm" /> Copy JSON
              </>
            )}
          </button>
        )}
      </div>

      {/* Data Preview */}
      {showDataPreview && (
        <div className="data-preview">
          <pre className="data-json">{JSON.stringify(currentCase.data, null, 2)}</pre>
        </div>
      )}

      {/* Visualization Result */}
      <div className="visualization-result">
        <div className="result-header">
          <strong>Auto-Detection Result:</strong>
        </div>
        {currentCase.data.length > 0 ? (
          <DataVisualizerEnhanced data={currentCase.data} />
        ) : (
          <div className="empty-state-test">
            <div className="empty-icon">📊</div>
            <div className="empty-message">No data available to visualize</div>
            <div className="empty-hint">
              This test case demonstrates how the component handles empty data gracefully
            </div>
          </div>
        )}
      </div>

      {/* Test Instructions */}
      <div className="test-instructions">
        <h3>📝 Testing Instructions</h3>
        <ol>
          <li>
            <strong>Select different test cases</strong> from the dropdown above
          </li>
          <li>
            <strong>Observe the "AI Reasoning" badge</strong> - it should dynamically update
            to explain why a specific chart type was chosen
          </li>
          <li>
            <strong>Check the footer metadata</strong> - verify row count, cardinality, and
            special badges (Time Series, Geographic, etc.)
          </li>
          <li>
            <strong>Try manual override</strong> - click the chart type buttons to force
            different visualizations
          </li>
          <li>
            <strong>Verify expected behavior</strong> - compare the auto-selected chart with
            the "Expected Chart" shown above
          </li>
        </ol>
      </div>

      {/* Heuristic Rules Reference */}
      <div className="heuristic-rules-reference">
        <h3>🧠 Heuristic Rules Summary</h3>
        <div className="rules-grid">
          <div className="rule-card">
            <div className="rule-number">1</div>
            <div className="rule-content">
              <strong>Time Series Detection</strong>
              <p>Year/month/quarter columns → Line/Area chart</p>
            </div>
          </div>

          <div className="rule-card">
            <div className="rule-number">2</div>
            <div className="rule-content">
              <strong>Part-to-Whole</strong>
              <p>Proportional data (2-12 items) → Pie chart</p>
            </div>
          </div>

          <div className="rule-card">
            <div className="rule-number">3</div>
            <div className="rule-content">
              <strong>Low Cardinality</strong>
              <p>2-8 categories → Pie chart for distribution</p>
            </div>
          </div>

          <div className="rule-card">
            <div className="rule-number">4</div>
            <div className="rule-content">
              <strong>Geographic Data</strong>
              <p>Region/country/city columns → Bar chart</p>
            </div>
          </div>

          <div className="rule-card">
            <div className="rule-number">5</div>
            <div className="rule-content">
              <strong>Medium Cardinality</strong>
              <p>9-20 categories → Bar chart comparison</p>
            </div>
          </div>

          <div className="rule-card">
            <div className="rule-number">6</div>
            <div className="rule-content">
              <strong>High Cardinality</strong>
              <p>21-50 categories → Bar chart (scrollable)</p>
            </div>
          </div>

          <div className="rule-card">
            <div className="rule-number">7</div>
            <div className="rule-content">
              <strong>Very High Cardinality</strong>
              <p>50+ categories or 100+ rows → Table view</p>
            </div>
          </div>

          <div className="rule-card">
            <div className="rule-number">8</div>
            <div className="rule-content">
              <strong>Multi-Metric</strong>
              <p>Multiple numeric columns → Line chart</p>
            </div>
          </div>

          <div className="rule-card">
            <div className="rule-number">9</div>
            <div className="rule-content">
              <strong>Large Datasets</strong>
              <p>100+ rows with categories → Aggregated bar</p>
            </div>
          </div>

          <div className="rule-card">
            <div className="rule-number">10</div>
            <div className="rule-content">
              <strong>Simple Categorical</strong>
              <p>Categories + metrics → Bar chart default</p>
            </div>
          </div>

          <div className="rule-card">
            <div className="rule-number">11</div>
            <div className="rule-content">
              <strong>Complex/Mixed</strong>
              <p>Unclear structure → Table fallback</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VizTestPlayground;
