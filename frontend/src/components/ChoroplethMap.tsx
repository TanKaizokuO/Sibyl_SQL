import React, { useState, useMemo } from 'react';
import { ComposableMap, Geographies, Geography } from 'react-simple-maps';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from 'recharts';
import { Info, Map as MapIcon } from 'lucide-react';

// US State Code mapping for compatibility (CA -> California)
const US_STATE_CODES: { [key: string]: string } = {
  AL: 'Alabama', AK: 'Alaska', AZ: 'Arizona', AR: 'Arkansas', CA: 'California',
  CO: 'Colorado', CT: 'Connecticut', DE: 'Delaware', FL: 'Florida', GA: 'Georgia',
  HI: 'Hawaii', ID: 'Idaho', IL: 'Illinois', IN: 'Indiana', IA: 'Iowa',
  KS: 'Kansas', KY: 'Kentucky', LA: 'Louisiana', ME: 'Maine', MD: 'Maryland',
  MA: 'Massachusetts', MI: 'Michigan', MN: 'Minnesota', MS: 'Mississippi', MO: 'Missouri',
  MT: 'Montana', NE: 'Nebraska', NV: 'Nevada', NH: 'New Hampshire', NJ: 'New Jersey',
  NM: 'New Mexico', NY: 'New York', NC: 'North Carolina', ND: 'North Dakota', OH: 'Ohio',
  OK: 'Oklahoma', OR: 'Oregon', PA: 'Pennsylvania', RI: 'Rhode Island', SC: 'South Carolina',
  SD: 'South Dakota', TN: 'Tennessee', TX: 'Texas', UT: 'Utah', VT: 'Vermont',
  VA: 'Virginia', WA: 'Washington', WV: 'West Virginia', WI: 'Wisconsin', WY: 'Wyoming'
};

const INDIA_STATES = [
  'andhra pradesh', 'arunachal pradesh', 'assam', 'bihar', 'chhattisgarh', 'goa', 'gujarat',
  'haryana', 'himachal pradesh', 'jharkhand', 'karnataka', 'kerala', 'madhya pradesh',
  'maharashtra', 'manipur', 'meghalaya', 'mizoram', 'nagaland', 'odisha', 'punjab', 'rajasthan',
  'sikkim', 'tamil nadu', 'telangana', 'tripura', 'uttar pradesh', 'uttarakhand', 'west bengal',
  'delhi', 'jammu & kashmir', 'ladakh', 'puducherry'
];

interface ChoroplethMapProps {
  data: any[];
  regionKey: string;
  valueKey: string;
  title?: string;
}

// TopoJSON CDN URLs
const US_TOPO_URL = 'https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json';
const INDIA_TOPO_URL = 'https://raw.githubusercontent.com/deldersveld/topojson/master/countries/india/india-states.json';

export const ChoroplethMap: React.FC<ChoroplethMapProps> = ({
  data,
  regionKey,
  valueKey,
  title,
}) => {
  const [tooltip, setTooltip] = useState<{ content: string; x: number; y: number } | null>(null);

  // 1. Process data & find range for color scaling
  const processedData = useMemo(() => {
    if (!data || !Array.isArray(data)) return [];
    return data.map((row) => ({
      ...row,
      regionName: String(row[regionKey] || '').trim(),
      val: parseFloat(row[valueKey]) || 0,
    }));
  }, [data, regionKey, valueKey]);

  const { minVal, maxVal } = useMemo(() => {
    if (processedData.length === 0) return { minVal: 0, maxVal: 0 };
    const values = processedData.map((d) => d.val);
    return {
      minVal: Math.min(...values),
      maxVal: Math.max(...values),
    };
  }, [processedData]);

  // 2. Identify the geographic mode
  const geoMode = useMemo(() => {
    if (processedData.length === 0) return 'fallback';

    let indiaCount = 0;
    let usCount = 0;
    let cardinalCount = 0;

    processedData.forEach((row) => {
      const reg = row.regionName.toLowerCase();
      const regUpper = row.regionName.toUpperCase();

      if (INDIA_STATES.includes(reg)) {
        indiaCount++;
      }
      if (US_STATE_CODES[regUpper] || Object.values(US_STATE_CODES).map(s => s.toLowerCase()).includes(reg)) {
        usCount++;
      }
      if (['north', 'south', 'east', 'west', 'n', 's', 'e', 'w', 'central', 'northeast', 'northwest', 'southeast', 'southwest'].includes(reg)) {
        cardinalCount++;
      }
    });

    if (cardinalCount > 0 && cardinalCount >= Math.max(indiaCount, usCount)) {
      return 'cardinal';
    }
    if (indiaCount > 0 && indiaCount >= usCount) {
      return 'india';
    }
    if (usCount > 0) {
      return 'us';
    }

    return 'fallback';
  }, [processedData]);

  // Helper to format values
  const formatVal = (val: number) => {
    if (val >= 1000000) return `$${(val / 1000000).toFixed(1)}M`;
    if (val >= 1000) return `$${(val / 1000).toFixed(0)}k`;
    return `$${val.toFixed(2)}`;
  };

  // Helper to compute sequential color scale (light blue -> deep indigo)
  const getColor = (val: number) => {
    if (minVal === maxVal) return '#3b82f6'; // Default solid blue
    const ratio = Math.max(0, Math.min(1, (val - minVal) / (maxVal - minVal || 1)));
    
    // Interpolating: Light Blue (#dbeafe = RGB 219, 234, 254) to Deep Indigo (#1e3a8a = RGB 30, 58, 138)
    const r = Math.round(219 + (30 - 219) * ratio);
    const g = Math.round(234 + (58 - 234) * ratio);
    const b = Math.round(254 + (138 - 254) * ratio);
    return `rgb(${r}, ${g}, ${b})`;
  };

  // Mouse tooltip event handlers
  const handleMouseEnter = (content: string, e: React.MouseEvent) => {
    setTooltip({
      content,
      x: e.clientX,
      y: e.clientY,
    });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (tooltip) {
      setTooltip({
        ...tooltip,
        x: e.clientX,
        y: e.clientY,
      });
    }
  };

  const handleMouseLeave = () => {
    setTooltip(null);
  };

  // ===========================================================================
  // RENDER: US / India States Map
  // ===========================================================================
  const renderSimpleMap = (topoUrl: string, scope: 'us' | 'india') => {
    // Map of regionName to value for O(1) lookup
    const dataMap = new Map<string, number>();
    processedData.forEach((d) => {
      dataMap.set(d.regionName.toLowerCase(), d.val);
      // For US, support code-based lookups too
      if (scope === 'us') {
        const stateName = US_STATE_CODES[d.regionName.toUpperCase()];
        if (stateName) {
          dataMap.set(stateName.toLowerCase(), d.val);
        }
      }
    });

    const projectionConfig = scope === 'us' 
      ? { scale: 900, translate: [480, 280] as [number, number] }
      : { scale: 1000, center: [78.9629, 22.5937] as [number, number] }; // Center on India

    const projection = scope === 'us' ? 'geoAlbersUsa' : 'geoMercator';

    return (
      <div className="choropleth-map-wrapper">
        <ComposableMap
          projection={projection}
          projectionConfig={projectionConfig}
          width={800}
          height={ scope === 'us' ? 500 : 600 }
          style={{ width: '100%', height: 'auto', maxHeight: '500px' }}
        >
          <Geographies geography={topoUrl}>
            {({ geographies }) =>
              geographies.map((geo) => {
                const name = geo.properties.name || geo.properties.ST_NM;
                const value = dataMap.get(name?.toLowerCase() || '');
                const hasValue = value !== undefined;
                const fillColor = hasValue ? getColor(value) : '#f1f5f9';

                return (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill={fillColor}
                    stroke="#ffffff"
                    strokeWidth={0.5}
                    style={{
                      default: { outline: 'none', transition: 'all 250ms' },
                      hover: { fill: hasValue ? '#6366f1' : '#cbd5e1', outline: 'none', cursor: hasValue ? 'pointer' : 'default' },
                      pressed: { outline: 'none' },
                    }}
                    onMouseEnter={(e) => {
                      if (hasValue) {
                        handleMouseEnter(`${name}: ${formatVal(value)}`, e);
                      } else {
                        handleMouseEnter(`${name}: No data`, e);
                      }
                    }}
                    onMouseMove={handleMouseMove}
                    onMouseLeave={handleMouseLeave}
                  />
                );
              })
            }
          </Geographies>
        </ComposableMap>
      </div>
    );
  };

  // ===========================================================================
  // RENDER: Cardinal Directions Map (Pure SVG)
  // ===========================================================================
  const renderCardinalMap = () => {
    // Map directions
    const dataMap = new Map<string, number>();
    processedData.forEach((d) => {
      const reg = d.regionName.toLowerCase();
      if (['north', 'n'].includes(reg)) dataMap.set('north', d.val);
      if (['south', 's'].includes(reg)) dataMap.set('south', d.val);
      if (['east', 'e'].includes(reg)) dataMap.set('east', d.val);
      if (['west', 'w'].includes(reg)) dataMap.set('west', d.val);
    });

    const directions = [
      {
        id: 'north',
        name: 'North Region',
        path: 'M 200 185 L 360 45 L 40 45 Z',
        labelX: 200,
        labelY: 90,
      },
      {
        id: 'east',
        name: 'East Region',
        path: 'M 215 200 L 355 60 L 355 340 Z',
        labelX: 295,
        labelY: 205,
      },
      {
        id: 'south',
        name: 'South Region',
        path: 'M 200 215 L 360 355 L 40 355 Z',
        labelX: 200,
        labelY: 310,
      },
      {
        id: 'west',
        name: 'West Region',
        path: 'M 185 200 L 45 60 L 45 340 Z',
        labelX: 105,
        labelY: 205,
      },
    ];

    return (
      <div className="choropleth-cardinal-wrapper">
        <svg
          viewBox="0 0 400 400"
          width="100%"
          height="100%"
          style={{ maxWidth: '400px', margin: '0 auto', display: 'block' }}
        >
          {directions.map((dir) => {
            const value = dataMap.get(dir.id);
            const hasValue = value !== undefined;
            const fillColor = hasValue ? getColor(value) : '#f1f5f9';

            return (
              <g key={dir.id} className="cardinal-region-group">
                <path
                  d={dir.path}
                  fill={fillColor}
                  stroke="#ffffff"
                  strokeWidth={2}
                  style={{
                    transition: 'all 200ms ease',
                    cursor: hasValue ? 'pointer' : 'default',
                  }}
                  onMouseEnter={(e) => {
                    if (hasValue) {
                      handleMouseEnter(`${dir.name}: ${formatVal(value)}`, e);
                    } else {
                      handleMouseEnter(`${dir.name}: No data`, e);
                    }
                  }}
                  onMouseMove={handleMouseMove}
                  onMouseLeave={handleMouseLeave}
                  className="cardinal-region-path"
                />
                <text
                  x={dir.labelX}
                  y={dir.labelY - 5}
                  textAnchor="middle"
                  fill={hasValue ? '#1e293b' : '#94a3b8'}
                  style={{
                    fontSize: '13px',
                    fontWeight: 700,
                    pointerEvents: 'none',
                    userSelect: 'none',
                  }}
                >
                  {dir.id.toUpperCase()}
                </text>
                <text
                  x={dir.labelX}
                  y={dir.labelY + 12}
                  textAnchor="middle"
                  fill={hasValue ? '#3b82f6' : '#94a3b8'}
                  style={{
                    fontSize: '11px',
                    fontWeight: 600,
                    pointerEvents: 'none',
                    userSelect: 'none',
                  }}
                >
                  {hasValue ? formatVal(value) : 'N/A'}
                </text>
              </g>
            );
          })}
          {/* Compass center hub */}
          <circle
            cx="200"
            cy="200"
            r="24"
            fill="#ffffff"
            stroke="#cbd5e1"
            strokeWidth={2}
          />
          <circle
            cx="200"
            cy="200"
            r="8"
            fill="#6366f1"
          />
        </svg>
      </div>
    );
  };

  // ===========================================================================
  // RENDER: Fallback Vertical Bar Chart
  // ===========================================================================
  const renderFallback = () => {
    return (
      <div className="choropleth-fallback">
        <div className="choropleth-fallback-badge">
          <Info className="icon-sm" />
          <span>Geographic Fallback: Format not recognized for India, US, or Cardinal map. Showing Bar Chart instead.</span>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart
            data={processedData}
            layout="vertical"
            margin={{ left: 60, right: 20, top: 10, bottom: 10 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis type="number" stroke="#6b7280" tickFormatter={formatVal} />
            <YAxis dataKey="regionName" type="category" stroke="#6b7280" />
            <RechartsTooltip
              formatter={(val: any) => [formatVal(Number(val)), valueKey]}
              contentStyle={{
                backgroundColor: '#ffffff',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
              }}
            />
            <Bar dataKey="val" fill="#3b82f6" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  };

  // Determine which visualizer to load
  const renderVisualizer = () => {
    switch (geoMode) {
      case 'india':
        return renderSimpleMap(INDIA_TOPO_URL, 'india');
      case 'us':
        return renderSimpleMap(US_TOPO_URL, 'us');
      case 'cardinal':
        return renderCardinalMap();
      case 'fallback':
      default:
        return renderFallback();
    }
  };

  return (
    <div className="choropleth-container">
      {title && <h4 className="choropleth-title">{title}</h4>}
      
      {renderVisualizer()}

      {/* Map Legend (Hidden for Fallback Mode) */}
      {geoMode !== 'fallback' && (
        <div className="choropleth-legend">
          <span>{formatVal(minVal)}</span>
          <div className="choropleth-gradient" />
          <span>{formatVal(maxVal)}</span>
          <span style={{ marginLeft: '12px', color: '#64748b' }}>
            <MapIcon className="icon-sm" style={{ display: 'inline', marginRight: '4px', verticalAlign: 'text-bottom' }} />
            Map Mode: {geoMode.toUpperCase()}
          </span>
        </div>
      )}

      {/* Floating Tooltip */}
      {tooltip && (
        <div
          className="choropleth-tooltip"
          style={{
            position: 'fixed',
            left: `${tooltip.x + 15}px`,
            top: `${tooltip.y - 10}px`,
            zIndex: 9999,
          }}
        >
          {tooltip.content}
        </div>
      )}
    </div>
  );
};

export default ChoroplethMap;
