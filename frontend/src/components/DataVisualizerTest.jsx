import { useState } from 'react'
import DataVisualizer from './DataVisualizer'

const DataVisualizerTest = () => {
  const [testCase, setTestCase] = useState('timeseries-single')

  const testDatasets = {
    // Time Series with Single Metric → Line Chart
    'timeseries-single': [
      { year: 2021, revenue: 500000 },
      { year: 2022, revenue: 650000 },
      { year: 2023, revenue: 800000 },
      { year: 2024, revenue: 950000 },
    ],

    // Time Series with Multiple Metrics → Area Chart
    'timeseries-multi': [
      { year: 2021, revenue: 500000, profit: 150000, expenses: 350000 },
      { year: 2022, revenue: 650000, profit: 195000, expenses: 455000 },
      { year: 2023, revenue: 800000, profit: 240000, expenses: 560000 },
      { year: 2024, revenue: 950000, profit: 285000, expenses: 665000 },
    ],

    // Few Categories with Single Metric → Pie Chart
    'few-categories': [
      { product: "Laptops", sales: 450000 },
      { product: "Phones", sales: 380000 },
      { product: "Tablets", sales: 250000 },
      { product: "Accessories", sales: 120000 },
    ],

    // Regional Data → Bar Chart
    'regional': [
      { region: "East", revenue: 770000, customers: 1200 },
      { region: "West", revenue: 920000, customers: 1450 },
      { region: "North", revenue: 675000, customers: 980 },
      { region: "South", revenue: 830000, customers: 1300 },
    ],

    // Medium Categories → Bar Chart
    'medium-categories': [
      { department: "Sales", headcount: 45, budget: 250000 },
      { department: "Marketing", headcount: 30, budget: 180000 },
      { department: "Engineering", headcount: 75, budget: 450000 },
      { department: "HR", headcount: 15, budget: 120000 },
      { department: "Finance", headcount: 20, budget: 150000 },
      { department: "Operations", headcount: 40, budget: 220000 },
      { department: "Customer Support", headcount: 35, budget: 190000 },
      { department: "R&D", headcount: 25, budget: 280000 },
    ],

    // Large Dataset → Bar/Aggregate
    'large-dataset': Array.from({ length: 50 }, (_, i) => ({
      customer_id: `CUST-${1000 + i}`,
      order_count: Math.floor(Math.random() * 20) + 1,
      total_spent: Math.floor(Math.random() * 50000) + 5000
    })),

    // Part-to-Whole Relationship → Pie Chart
    'part-to-whole': [
      { category: "Marketing", budget_share: 25000 },
      { category: "Development", budget_share: 45000 },
      { category: "Operations", budget_share: 15000 },
      { category: "Sales", budget_share: 15000 },
    ],
  }

  const testCaseDescriptions = {
    'timeseries-single': 'Time Series (Single Metric) - Should show Line Chart',
    'timeseries-multi': 'Time Series (Multiple Metrics) - Should show Area Chart',
    'few-categories': 'Few Categories (2-7) - Should show Pie Chart',
    'regional': 'Regional/Geographic Data - Should show Bar Chart',
    'medium-categories': 'Medium Categories (8-20) - Should show Bar Chart',
    'large-dataset': 'Large Dataset (50+ rows) - Should show Bar/Table',
    'part-to-whole': 'Part-to-Whole Relationship - Should show Pie Chart',
  }

  return (
    <div style={{ padding: '2rem' }}>
      <h2 style={{ marginBottom: '1rem' }}>Data Visualizer Test Cases</h2>

      <div style={{ marginBottom: '2rem' }}>
        <label style={{ marginRight: '1rem', fontWeight: 'bold' }}>
          Select Test Case:
        </label>
        <select
          value={testCase}
          onChange={(e) => setTestCase(e.target.value)}
          style={{
            padding: '0.5rem',
            fontSize: '1rem',
            borderRadius: '4px',
            border: '1px solid #ccc'
          }}
        >
          {Object.entries(testCaseDescriptions).map(([key, description]) => (
            <option key={key} value={key}>{description}</option>
          ))}
        </select>
      </div>

      <DataVisualizer stepData={testDatasets[testCase]} />
    </div>
  )
}

export default DataVisualizerTest
