import React, { useState, useEffect, useMemo, useRef } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, 
  ComposedChart, Area, ReferenceLine
} from 'recharts';
import { TrendingUp, AlertCircle, Calendar, Grid, Layers, Shield, RefreshCw } from 'lucide-react';

const PERIOD_MAP = {
  'HV 22 (1M)': 'hv_22',
  'HV 66 (3M)': 'hv_66',
  'HV 132 (6M)': 'hv_132',
  'HV 252 (1Y)': 'hv_252'
};

const SYMBOLS_POOL = ['VIC', 'VRE', 'FPT', 'HPG', 'VNM', 'VPB'];

export default function App() {
  const [summary, setSummary] = useState(null);
  const [activeSymbol, setActiveSymbol] = useState('VIC');
  const [compareBasket, setCompareBasket] = useState(['VRE', 'FPT', 'HPG']);
  const [termWindow, setTermWindow] = useState('HV 252 (1Y)');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  
  // Data caches
  const [stockData, setStockData] = useState([]);
  const [compareData, setCompareData] = useState({});
  const [vn30Data, setVn30Data] = useState([]);
  const [loading, setLoading] = useState(true);

  // Dropdown states
  const [showCompareDropdown, setShowCompareDropdown] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowCompareDropdown(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // 1. Load summary on mount
  useEffect(() => {
    fetch('/data_output/summary.json')
      .then(res => res.json())
      .then(data => {
        setSummary(data);
        if (data.availableSymbols && data.availableSymbols.length > 0) {
          setActiveSymbol(data.availableSymbols[0]);
        }
      })
      .catch(err => console.error('Error loading summary:', err));
  }, []);

  // 2. Load active stock and VN30 data
  useEffect(() => {
    if (!activeSymbol) return;
    setLoading(true);

    Promise.all([
      fetch(`/data_output/${activeSymbol}_processed.json`).then(res => res.json()),
      fetch('/data_output/VN30_processed.json').then(res => res.json())
    ])
      .then(([activeStock, indexData]) => {
        setStockData(activeStock);
        setVn30Data(indexData);
        
        // Initialize date inputs if not set
        if (activeStock.length > 0) {
          const dates = activeStock.map(d => parseDate(d.tradingDate));
          const minDate = formatDateISO(new Date(Math.min(...dates)));
          const maxDate = formatDateISO(new Date(Math.max(...dates)));
          setStartDate(minDate);
          setEndDate(maxDate);
        }
        setLoading(false);
      })
      .catch(err => {
        console.error('Error loading active stock data:', err);
        setLoading(false);
      });
  }, [activeSymbol]);

  // 3. Load comparison stocks data
  useEffect(() => {
    if (compareBasket.length === 0) return;

    const fetches = compareBasket.map(symbol => 
      fetch(`/data_output/${symbol}_processed.json`)
        .then(res => res.json())
        .then(data => ({ symbol, data }))
        .catch(err => {
          console.error(`Error loading comparison data for ${symbol}:`, err);
          return { symbol, data: [] };
        })
    );

    Promise.all(fetches).then(results => {
      const cache = {};
      results.forEach(r => {
        cache[r.symbol] = r.data;
      });
      setCompareData(cache);
    });
  }, [compareBasket]);

  // Helper date parsers
  function parseDate(dateStr) {
    const [day, month, year] = dateStr.split('/').map(Number);
    return new Date(year, month - 1, day);
  }

  function formatDateISO(date) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }

  function formatDateDisplay(dateStr) {
    return dateStr; // SSI API format is already DD/MM/YYYY
  }

  // Filter datasets by date
  const filteredData = useMemo(() => {
    if (!startDate || !endDate || stockData.length === 0) return stockData;
    const start = new Date(startDate);
    const end = new Date(endDate);

    return stockData.filter(d => {
      const date = parseDate(d.tradingDate);
      return date >= start && date <= end;
    });
  }, [stockData, startDate, endDate]);

  const filteredCompareData = useMemo(() => {
    if (!startDate || !endDate) return compareData;
    const start = new Date(startDate);
    const end = new Date(endDate);

    const filtered = {};
    Object.keys(compareData).forEach(symbol => {
      filtered[symbol] = compareData[symbol].filter(d => {
        const date = parseDate(d.tradingDate);
        return date >= start && date <= end;
      });
    });
    return filtered;
  }, [compareData, startDate, endDate]);

  // Active Symbol info
  const activeStockInfo = useMemo(() => {
    if (!summary || !summary.stocks || !summary.stocks[activeSymbol]) return null;
    return summary.stocks[activeSymbol];
  }, [summary, activeSymbol]);

  // Calculations for current selection
  const percentileAndRisk = useMemo(() => {
    if (filteredData.length === 0) return { percentile: 50, label: 'Moderate Volatility', statusClass: 'status-med' };
    
    // Percentile rank of current HV 252 relative to history
    const hv252s = filteredData.map(d => d.hv_252 * 100).filter(v => !isNaN(v));
    if (hv252s.length === 0) return { percentile: 50, label: 'Moderate Volatility', statusClass: 'status-med' };

    const currentHV = hv252s[hv252s.length - 1];
    const belowCount = hv252s.filter(v => v <= currentHV).length;
    const percentile = (belowCount / hv252s.length) * 100;

    let label = 'Moderate Volatility';
    let statusClass = 'status-med';
    if (percentile < 30.0) {
      label = 'Low Volatility Risk';
      statusClass = 'status-low';
    } else if (percentile > 70.0) {
      label = 'HIGH VOLATILITY RISK';
      statusClass = 'status-high';
    }

    return { percentile, label, statusClass };
  }, [filteredData]);

  // Calculate dynamic correlation matrix for the active compare basket
  const correlationMatrix = useMemo(() => {
    const symbols = [activeSymbol, ...compareBasket];
    if (symbols.length < 2) return null;

    // Align all data on date
    const dateMap = new Map(); // date -> { symbol -> close }
    
    // Add active symbol
    filteredData.forEach(d => {
      dateMap.set(d.tradingDate, { [activeSymbol]: d.close });
    });

    // Add comparison symbols
    symbols.forEach(sym => {
      if (sym === activeSymbol) return;
      const data = filteredCompareData[sym] || [];
      data.forEach(d => {
        if (dateMap.has(d.tradingDate)) {
          dateMap.get(d.tradingDate)[sym] = d.close;
        }
      });
    });

    // Filter to rows containing all symbols
    const alignedRows = [];
    dateMap.forEach((prices, date) => {
      if (symbols.every(sym => prices[sym] !== undefined)) {
        alignedRows.push({ date, ...prices });
      }
    });

    // Sort chronologically
    alignedRows.sort((a, b) => parseDate(a.date) - parseDate(b.date));

    if (alignedRows.length < 5) return null;

    // Calculate returns
    const returns = [];
    for (let i = 1; i < alignedRows.length; i++) {
      const row = { date: alignedRows[i].date };
      symbols.forEach(sym => {
        row[sym] = Math.log(alignedRows[i][sym] / alignedRows[i - 1][sym]);
      });
      returns.push(row);
    }

    // Pearson Correlation matrix
    const matrix = {};
    const N = returns.length;

    symbols.forEach(sym1 => {
      matrix[sym1] = {};
      const mean1 = returns.reduce((sum, r) => sum + r[sym1], 0) / N;
      const var1 = returns.reduce((sum, r) => sum + Math.pow(r[sym1] - mean1, 2), 0);

      symbols.forEach(sym2 => {
        const mean2 = returns.reduce((sum, r) => sum + r[sym2], 0) / N;
        const var2 = returns.reduce((sum, r) => sum + Math.pow(r[sym2] - mean2, 2), 0);

        let cov = 0;
        for (let i = 0; i < N; i++) {
          cov += (returns[i][sym1] - mean1) * (returns[i][sym2] - mean2);
        }

        const r = cov / Math.sqrt(var1 * var2);
        matrix[sym1][sym2] = isNaN(r) ? 1.0 : r;
      });
    });

    return matrix;
  }, [activeSymbol, compareBasket, filteredData, filteredCompareData]);

  // Statistics Matrix Row 3 Table
  const statsComparisonMatrix = useMemo(() => {
    const targetField = PERIOD_MAP[termWindow];
    const symbols = [activeSymbol, ...compareBasket];
    
    return symbols.map(sym => {
      const data = sym === activeSymbol ? filteredData : (filteredCompareData[sym] || []);
      const hvs = data.map(d => d[targetField] * 100).filter(v => !isNaN(v) && v !== null);

      if (hvs.length === 0) {
        return { symbol: sym, current: 0, mean: 0, min: 0, max: 0 };
      }

      const min = Math.min(...hvs);
      const max = Math.max(...hvs);
      const mean = hvs.reduce((s, v) => s + v, 0) / hvs.length;
      const current = hvs[hvs.length - 1];

      return { symbol: sym, current, mean, min, max };
    });
  }, [activeSymbol, compareBasket, filteredData, filteredCompareData, termWindow]);

  // Dynamic Peer correlations list for Row 2 Card E
  const peerCorrelationsList = useMemo(() => {
    const targetMatrix = correlationMatrix;
    if (!targetMatrix || !targetMatrix[activeSymbol]) return [];

    return Object.keys(targetMatrix[activeSymbol])
      .filter(sym => sym !== activeSymbol)
      .map(sym => {
        const r = targetMatrix[activeSymbol][sym];
        let label = 'Weak';
        let style = { color: '#9CA3AF' };
        if (r > 0.6) {
          label = 'Strong';
          style = { color: '#EF4444', fontWeight: 600 };
        } else if (r > 0.35) {
          label = 'Moderate';
          style = { color: '#F5A800', fontWeight: 600 };
        }
        return { symbol: sym, r, label, style };
      });
  }, [correlationMatrix, activeSymbol]);

  // Handle compare basket multiselect toggles
  const handleSelectCompare = (symbol) => {
    if (compareBasket.includes(symbol)) {
      setCompareBasket(compareBasket.filter(s => s !== symbol));
    } else {
      if (compareBasket.length >= 5) return; // limit to 5
      setCompareBasket([...compareBasket, symbol]);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', color: '#94A3B8' }}>
        <RefreshCw className="animate-spin" size={24} style={{ marginRight: 8 }} />
        <span>Syncing Terminal Data...</span>
      </div>
    );
  }

  // Dual axis timeline chart data
  const timelineChartData = filteredData.map(d => ({
    date: d.tradingDate,
    'HV 22 (1M)': d.hv_22 ? parseFloat((d.hv_22 * 100).toFixed(2)) : null,
    'HV 66 (3M)': d.hv_66 ? parseFloat((d.hv_66 * 100).toFixed(2)) : null,
    'HV 132 (6M)': d.hv_132 ? parseFloat((d.hv_132 * 100).toFixed(2)) : null,
    'HV 252 (1Y)': d.hv_252 ? parseFloat((d.hv_252 * 100).toFixed(2)) : null,
    Price: d.close ? parseFloat(d.close.toFixed(1)) : null // format to k VND (e.g. 200.0)
  }));

  // Comparison Line chart data
  const targetField = PERIOD_MAP[termWindow];
  const comparisonChartData = filteredData.map((d, index) => {
    const row = { date: d.tradingDate };
    row[activeSymbol] = d[targetField] ? parseFloat((d[targetField] * 100).toFixed(2)) : null;

    compareBasket.forEach(sym => {
      const symData = filteredCompareData[sym] || [];
      // Find matching row by index or date (date is safer)
      const match = symData.find(sd => sd.tradingDate === d.tradingDate);
      row[sym] = match && match[targetField] ? parseFloat((match[targetField] * 100).toFixed(2)) : null;
    });

    return row;
  });

  // Latest stats
  const latestPrice = stockData.length > 0 ? stockData[stockData.length - 1].close * 1000 : 0;
  const latestSessionDate = stockData.length > 0 ? stockData[stockData.length - 1].tradingDate : 'N/A';

  return (
    <div>
      {/* 1. Header Row */}
      <div className="header-container">
        <div>
          <h1 className="header-title">
            HV Terminal
          </h1>
        </div>
        <div className="header-date">
          Session Date: <span className="header-date-val">{latestSessionDate}</span>
        </div>
      </div>

      {/* 2. Controls Grid */}
      <div className="controls-grid">
        <div className="control-item">
          <label className="control-label">Active Ticker</label>
          <select 
            className="control-select"
            value={activeSymbol}
            onChange={(e) => setActiveSymbol(e.target.value)}
          >
            {summary?.availableSymbols.map(sym => (
              <option key={sym} value={sym}>{sym}</option>
            ))}
          </select>
        </div>

        <div className="control-item" ref={dropdownRef}>
          <label className="control-label">Compare Basket</label>
          <div className="control-multiselect-container">
            <div 
              className="control-select" 
              style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', overflow: 'hidden', whiteSpace: 'nowrap' }}
              onClick={() => setShowCompareDropdown(!showCompareDropdown)}
            >
              {compareBasket.length === 0 ? 'Select Peers...' : compareBasket.join(', ')}
            </div>
            {showCompareDropdown && (
              <div className="multiselect-dropdown">
                {SYMBOLS_POOL.map(sym => (
                  <div 
                    key={sym} 
                    className={`multiselect-option ${compareBasket.includes(sym) ? 'selected' : ''}`}
                    onClick={() => handleSelectCompare(sym)}
                  >
                    <input 
                      type="checkbox" 
                      checked={compareBasket.includes(sym)} 
                      onChange={() => {}} 
                      style={{ marginRight: 8 }}
                    />
                    {sym}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="control-item">
          <label className="control-label">Term Window</label>
          <select 
            className="control-select"
            value={termWindow}
            onChange={(e) => setTermWindow(e.target.value)}
          >
            <option>HV 22 (1M)</option>
            <option>HV 66 (3M)</option>
            <option>HV 132 (6M)</option>
            <option>HV 252 (1Y)</option>
          </select>
        </div>

        <div className="control-item">
          <label className="control-label">Start Date</label>
          <input 
            type="date" 
            className="control-input"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </div>

        <div className="control-item">
          <label className="control-label">End Date</label>
          <input 
            type="date" 
            className="control-input"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </div>
      </div>

      {/* 3. Bento Grid - Row 1 */}
      <div className="bento-row-1">
        {/* Volatility Master Timeline (8/12) */}
        <div className="bento-card">
          <div className="bento-header">
            <div className="bento-title">
              <TrendingUp size={16} />
              Volatility Master Timeline
            </div>
          </div>
          <div style={{ width: '100%', height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={timelineChartData} margin={{ top: 10, right: -5, left: -20, bottom: 0 }}>
                <CartesianGrid stroke="#1E293B" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" stroke="#64748B" fontSize={10} tickLine={false} />
                <YAxis yAxisId="left" stroke="#94A3B8" fontSize={10} label={{ value: 'Volatility (%)', angle: -90, position: 'insideLeft', style: { fill: '#94A3B8' } }} />
                <YAxis yAxisId="right" orientation="right" stroke="#64748B" fontSize={10} domain={['auto', 'auto']} label={{ value: 'Price (k VND)', angle: 90, position: 'insideRight', style: { fill: '#64748B' } }} />
                <Tooltip contentStyle={{ backgroundColor: '#0E131F', borderColor: '#1E293B', borderRadius: 8, color: '#F8FAFC' }} />
                <Legend verticalAlign="top" height={36} iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                <Line yAxisId="right" type="monotone" dataKey="Price" stroke="#94A3B8" strokeWidth={1.5} dot={false} opacity={0.45} />
                <Line yAxisId="left" type="monotone" dataKey="HV 22 (1M)" stroke="#EC4899" strokeWidth={2} dot={false} />
                <Line yAxisId="left" type="monotone" dataKey="HV 66 (3M)" stroke="#F59E0B" strokeWidth={2} dot={false} />
                <Line yAxisId="left" type="monotone" dataKey="HV 132 (6M)" stroke="#10B981" strokeWidth={2} dot={false} />
                <Line yAxisId="left" type="monotone" dataKey="HV 252 (1Y)" stroke="#6366F1" strokeWidth={2} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Volatility Cone (4/12) */}
        <div className="bento-card">
          <div className="bento-header">
            <div className="bento-title">
              <Layers size={16} />
              Volatility Cone
            </div>
          </div>
          <div style={{ width: '100%', height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart 
                data={activeStockInfo?.volatilityCone || []}
                margin={{ top: 10, right: 10, left: -25, bottom: 0 }}
              >
                <CartesianGrid stroke="#1E293B" vertical={false} />
                <XAxis dataKey="window" stroke="#64748B" fontSize={10} tickFormatter={(v) => `${v}d`} />
                <YAxis stroke="#94A3B8" fontSize={10} />
                <Tooltip contentStyle={{ backgroundColor: '#0E131F', borderColor: '#1E293B', borderRadius: 8 }} />
                <Legend verticalAlign="top" height={36} iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                
                {/* Max & Min filled region */}
                <Area type="monotone" dataKey="max" stroke="rgba(239, 68, 68, 0.4)" fill="rgba(30, 41, 59, 0.25)" strokeWidth={1} name="Max Range" />
                <Area type="monotone" dataKey="min" stroke="rgba(16, 185, 129, 0.4)" fill="transparent" strokeWidth={1} name="Min Range" />
                
                <Line type="monotone" dataKey="mean" stroke="#6366F1" strokeWidth={2} strokeDasharray="4 4" name="Mean" dot={false} />
                <Line type="monotone" dataKey="current" stroke="#F5A800" strokeWidth={2.5} name="Current" dot={{ symbol: 'diamond', r: 5, fill: '#F5A800' }} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* 4. Bento Grid - Row 2 */}
      <div className="bento-row-2">
        {/* Volatility Distribution (4/12) */}
        <div className="bento-card">
          <div className="bento-header">
            <div className="bento-title">
              <Grid size={16} />
              Volatility Distribution Range
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 18, marginTop: 10 }}>
            {activeStockInfo && Object.entries(activeStockInfo.hv_metrics).map(([name, data]) => {
              // Calculate percentage positioning inside Min-Max slider
              const range = data.max - data.min;
              const posPercent = range !== 0 ? ((data.current - data.min) / range) * 100 : 50;
              const meanPercent = range !== 0 ? ((data.mean - data.min) / range) * 100 : 50;

              return (
                <div key={name} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                    <span style={{ fontWeight: 600, color: '#CBD5E1' }}>{name.split(' ')[0] + ' ' + name.split(' ')[1]}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>{data.current.toFixed(2)}%</span>
                  </div>
                  
                  {/* Visual Range bar */}
                  <div style={{ position: 'relative', height: 6, backgroundColor: '#1E293B', borderRadius: 3, margin: '8px 0' }}>
                    {/* Mean line marker */}
                    <div style={{ 
                      position: 'absolute', 
                      left: `${meanPercent}%`, 
                      top: -4, 
                      width: 2, 
                      height: 14, 
                      backgroundColor: '#6366F1',
                      zIndex: 1
                    }} title={`Mean: ${data.mean.toFixed(2)}%`} />
                    
                    {/* Current value marker node */}
                    <div style={{ 
                      position: 'absolute', 
                      left: `${posPercent}%`, 
                      top: -6, 
                      width: 18, 
                      height: 18, 
                      borderRadius: '50%', 
                      backgroundColor: '#F5A800',
                      transform: 'translateX(-50%)',
                      boxShadow: '0 0 10px #F5A800',
                      zIndex: 2
                    }} title={`Current: ${data.current.toFixed(2)}%`} />
                  </div>
                  
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: '#64748B' }}>
                    <span>Min: {data.min.toFixed(1)}%</span>
                    <span>Avg: {data.mean.toFixed(1)}%</span>
                    <span>Max: {data.max.toFixed(1)}%</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Risk Metrics & Stats (4/12) */}
        <div className="bento-card">
          <div className="bento-header">
            <div className="bento-title">
              <Shield size={16} />
              Risk Metrics &amp; Stats
            </div>
          </div>
          
          <div className={`regime-box`}>
            <div>
              <div className="regime-label">Regime Assessment</div>
              <div className="regime-value">{percentileAndRisk.label}</div>
            </div>
            <span className={`status-pill ${percentileAndRisk.statusClass}`}>
              {percentileAndRisk.percentile.toFixed(1)} Percentile
            </span>
          </div>

          <div className="kpi-container">
            {activeStockInfo && Object.entries(activeStockInfo.hv_metrics).map(([name, data]) => {
              const deltaClass = data.delta > 0 ? 'delta-up' : 'delta-down';
              const deltaArrow = data.delta > 0 ? '▲' : '▼';
              const shortName = name.split(' ')[0] + ' ' + name.split(' ')[1];

              return (
                <div className="kpi-card" key={name}>
                  <span className="kpi-label">{shortName}</span>
                  <span className="kpi-value">{data.current.toFixed(2)}%</span>
                  <span className={`kpi-delta ${deltaClass}`}>
                    {deltaArrow} {Math.abs(data.delta).toFixed(2)}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Peer Correlation & Beta (4/12) */}
        <div className="bento-card">
          <div className="bento-header">
            <div className="bento-title">
              <TrendingUp size={16} />
              Peer Correlation &amp; Beta
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
            <div style={{ backgroundColor: 'var(--inner-bg)', padding: '8px 10px', borderRadius: 8, border: '1px solid var(--border-color)', textAlign: 'center' }}>
              <div style={{ fontSize: '0.65rem', color: '#64748B', textTransform: 'uppercase', fontWeight: 600 }}>Beta vs VN30</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#F5A800', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
                {activeStockInfo?.beta.toFixed(2) || '1.00'}
              </div>
            </div>
            <div style={{ backgroundColor: 'var(--inner-bg)', padding: '8px 10px', borderRadius: 8, border: '1px solid var(--border-color)', textAlign: 'center' }}>
              <div style={{ fontSize: '0.65rem', color: '#64748B', textTransform: 'uppercase', fontWeight: 600 }}>Dir. Accuracy</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--green)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
                {activeStockInfo ? `${(activeStockInfo.directionalAccuracy * 100).toFixed(1)}%` : '50.0%'}
              </div>
            </div>
          </div>

          <div className="table-label">Correlation vs VN30 Basket Giants</div>
          <table className="peer-table">
            <thead>
              <tr>
                <th style={{ width: '35%' }}>Peer Stock</th>
                <th style={{ width: '30%' }}>Pearson R</th>
                <th style={{ width: '35%' }}>Relationship</th>
              </tr>
            </thead>
            <tbody>
              {peerCorrelationsList.map(peer => (
                <tr key={peer.symbol}>
                  <td><b>{peer.symbol}</b></td>
                  <td>{peer.r.toFixed(2)}</td>
                  <td>
                    <span style={peer.style} className="peer-badge">{peer.label}</span>
                  </td>
                </tr>
              ))}
              {peerCorrelationsList.length === 0 && (
                <tr>
                  <td colSpan="3" style={{ textAlign: 'center', color: '#64748B' }}>Add comparison peers to view correlations</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 5. Bento Grid - Row 3 */}
      <div className="bento-row-3">
        {/* Historical Volatility Comparison (4/12) */}
        <div className="bento-card">
          <div className="bento-header">
            <div className="bento-title">
              <TrendingUp size={16} />
              Historical Volatility Comparison
            </div>
          </div>
          {compareBasket.length === 0 ? (
            <div className="warning-block">
              <AlertCircle className="warning-icon" />
              <span>Select at least 1 peer stock in the Compare Basket to view comparison.</span>
            </div>
          ) : (
            <div style={{ width: '100%', height: 220 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={comparisonChartData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                  <CartesianGrid stroke="#1E293B" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="date" stroke="#64748B" fontSize={10} tickLine={false} />
                  <YAxis stroke="#94A3B8" fontSize={10} />
                  <Tooltip contentStyle={{ backgroundColor: '#0E131F', borderColor: '#1E293B', borderRadius: 8 }} />
                  <Legend verticalAlign="top" height={36} iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                  
                  <Line type="monotone" dataKey={activeSymbol} stroke="#EC4899" strokeWidth={2.5} dot={false} />
                  {compareBasket.map((sym, idx) => {
                    const colors = ['#F59E0B', '#10B981', '#6366F1', '#8B5CF6', '#EC4899'];
                    return (
                      <Line 
                        key={sym}
                        type="monotone" 
                        dataKey={sym} 
                        stroke={colors[idx % colors.length]} 
                        strokeWidth={2} 
                        dot={false} 
                      />
                    );
                  })}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Volatility Correlation Heatmap (4/12) */}
        <div className="bento-card">
          <div className="bento-header">
            <div className="bento-title">
              <Grid size={16} />
              Volatility Correlation Heatmap
            </div>
          </div>
          
          {compareBasket.length === 0 ? (
            <div className="warning-block">
              <AlertCircle className="warning-icon" />
              <span>Select at least 1 peer stock in the Compare Basket to view heatmap.</span>
            </div>
          ) : correlationMatrix ? (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%', justifyContent: 'center' }}>
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: `repeat(${[activeSymbol, ...compareBasket].length}, 1fr)`,
                gap: 4,
                marginTop: 10,
                alignSelf: 'center',
                width: '100%',
                maxWidth: 240
              }}>
                {[activeSymbol, ...compareBasket].map(symY => 
                  [activeSymbol, ...compareBasket].map(symX => {
                    const val = correlationMatrix[symY]?.[symX] ?? 1.0;
                    
                    // Dynamic cell background color based on Pearson R
                    // Green for positive, dark/grey for neutral, red for negative
                    let bg = 'rgba(16, 185, 129, 0.05)';
                    let border = '1px solid rgba(16, 185, 129, 0.1)';
                    let textCol = '#CBD5E1';
                    
                    if (val > 0.7) {
                      bg = 'rgba(16, 185, 129, 0.3)';
                      border = '1px solid rgba(16, 185, 129, 0.6)';
                      textCol = '#F8FAFC';
                    } else if (val > 0.4) {
                      bg = 'rgba(245, 168, 0, 0.2)';
                      border = '1px solid rgba(245, 168, 0, 0.4)';
                    } else if (val < 0.2) {
                      bg = 'rgba(148, 163, 184, 0.1)';
                      border = '1px solid rgba(148, 163, 184, 0.2)';
                    }

                    return (
                      <div 
                        key={`${symY}-${symX}`}
                        style={{ 
                          backgroundColor: bg, 
                          border: border,
                          borderRadius: 4,
                          display: 'flex',
                          flexDirection: 'column',
                          justifyContent: 'center',
                          alignItems: 'center',
                          aspectRatio: '1',
                          fontSize: '0.8rem',
                          color: textCol,
                          cursor: 'default'
                        }}
                        title={`${symY} vs ${symX}: ${val.toFixed(3)}`}
                      >
                        <span style={{ fontSize: '0.55rem', color: '#64748B', fontWeight: 600 }}>{symY}-{symX}</span>
                        <span style={{ fontWeight: 700, fontFamily: 'var(--font-mono)', marginTop: 2 }}>{val.toFixed(2)}</span>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', color: '#64748B', padding: 20 }}>Unable to compute correlation matrix</div>
          )}
        </div>

        {/* Volatility Statistics Matrix (4/12) */}
        <div className="bento-card">
          <div className="bento-header">
            <div className="bento-title">
              <Layers size={16} />
              Volatility Statistics Matrix
            </div>
          </div>
          <div style={{ overflowX: 'auto', display: 'flex', alignItems: 'center', height: '100%' }}>
            <table className="peer-table" style={{ marginTop: 0 }}>
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Current</th>
                  <th>Average</th>
                  <th>Min</th>
                  <th>Max</th>
                </tr>
              </thead>
              <tbody>
                {statsComparisonMatrix.map(row => (
                  <tr key={row.symbol} style={{ borderBottom: '1px solid #1E293B' }}>
                    <td><b>{row.symbol}</b></td>
                    <td style={{ color: 'var(--text-primary)' }}>{row.current.toFixed(2)}%</td>
                    <td>{row.mean.toFixed(2)}%</td>
                    <td style={{ color: 'var(--green)' }}>{row.min.toFixed(2)}%</td>
                    <td style={{ color: 'var(--red)' }}>{row.max.toFixed(2)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
