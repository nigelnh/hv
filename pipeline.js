import fs from 'fs';
import path from 'path';

const DATA_FOLDER = 'data_output';
const SYMBOLS = ['VIC', 'VRE'];
const PEER_SYMBOLS = ['FPT', 'HPG', 'VNM', 'VPB', 'VIC', 'VRE']; // Wider pool for peer comparison
const INDEX_SYMBOL = 'VN30';
const START_DATE = '01/01/2022';

// Create data directory if it doesn't exist
if (!fs.existsSync(DATA_FOLDER)) {
  fs.mkdirSync(DATA_FOLDER);
}

// Helper to parse date string "DD/MM/YYYY" to Date object
function parseDate(dateStr) {
  const [day, month, year] = dateStr.split('/').map(Number);
  return new Date(year, month - 1, day);
}

// Polite delay
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// SSI API paginated fetcher
async function fetchStockData(symbol, fromDate, toDate) {
  const url = 'https://iboard-api.ssi.com.vn/statistics/company/ssmi/stock-info';
  const headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
  };

  const allData = [];
  let page = 1;
  const pageSize = 40;

  console.log(`\nFetching data from SSI API for symbol: ${symbol}`);

  while (true) {
    const params = new URLSearchParams({
      symbol: symbol,
      page: page.toString(),
      pageSize: pageSize.toString(),
      fromDate: fromDate,
      toDate: toDate
    });

    try {
      const response = await fetch(`${url}?${params.toString()}`, { headers });
      if (!response.ok) {
        console.error(`  [ERROR] HTTP ${response.status} at page ${page}`);
        break;
      }

      const json = await response.json();
      if (json.code !== 'SUCCESS' || !json.data) {
        break;
      }

      const pageData = json.data;
      if (pageData.length === 0) {
        break;
      }

      allData.push(...pageData);

      const paging = json.paging || {};
      const total = paging.total || 0;
      console.log(`  Page ${page}: fetched ${pageData.length} rows | Total: ${allData.length}/${total}`);

      if (allData.length >= total || pageData.length < pageSize) {
        break;
      }

      page++;
      await sleep(50); // polite delay
    } catch (e) {
      console.error(`  [ERROR] Connection error at page ${page}: ${e}`);
      await sleep(1000);
    }
  }

  if (allData.length === 0) {
    console.warn(`  [WARN] No data returned for ${symbol}`);
    return null;
  }

  // Format, sort, and filter data
  const formatted = allData.map(d => ({
    tradingDate: d.tradingDate,
    open: parseFloat(d.open) || 0,
    high: parseFloat(d.high) || 0,
    low: parseFloat(d.low) || 0,
    close: parseFloat(d.close) || 0,
    volume: parseInt(d.volume) || 0
  }));

  // Sort chronologically
  formatted.sort((a, b) => parseDate(a.tradingDate) - parseDate(b.tradingDate));

  return formatted;
}

// Calculate rolling historical volatility
function calculateHV(prices, windowSize) {
  const hvs = new Array(prices.length).fill(null);
  if (prices.length < windowSize + 1) return hvs;

  // Daily log returns
  const logReturns = [];
  for (let i = 0; i < prices.length; i++) {
    if (i === 0) {
      logReturns.push(null);
    } else {
      const prev = prices[i - 1];
      const curr = prices[i];
      if (prev > 0 && curr > 0) {
        logReturns.push(Math.log(curr / prev));
      } else {
        logReturns.push(null);
      }
    }
  }

  // Rolling standard deviation
  for (let i = windowSize; i < prices.length; i++) {
    const windowSlice = logReturns.slice(i - windowSize + 1, i + 1);
    const validReturns = windowSlice.filter(v => v !== null);
    
    if (validReturns.length < windowSize) continue;

    // Mean
    const mean = validReturns.reduce((sum, v) => sum + v, 0) / validReturns.length;
    // Sample variance (ddof = 1)
    const sqDiffSum = validReturns.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0);
    const variance = sqDiffSum / (validReturns.length - 1);
    const stdDev = Math.sqrt(variance);

    // Annualize
    hvs[i] = stdDev * Math.sqrt(252);
  }

  return hvs;
}

// Calculate Volatility Cone stats
function calculateVolatilityCone(df) {
  const windows = [22, 66, 132, 252];
  const cone = [];

  for (const window of windows) {
    const key = `hv_${window}`;
    // Extract non-null values (as percentages)
    const values = df.map(row => row[key]).filter(v => v !== null).map(v => v * 100);

    if (values.length === 0) {
      cone.push({ window, min: 0, max: 0, mean: 0, median: 0, current: 0 });
      continue;
    }

    const min = Math.min(...values);
    const max = Math.max(...values);
    const sum = values.reduce((s, v) => s + v, 0);
    const mean = sum / values.length;
    
    // Median
    const sorted = [...values].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    const median = sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;

    const current = values[values.length - 1];

    cone.push({ window, min, max, mean, median, current });
  }

  return cone;
}

// Calculate stock metrics (beta, directional accuracy, peer correlations)
function calculateCorrelationsAndBeta(stockData, vn30Data, allStocks) {
  // Align stock and VN30 on date
  const vn30Map = new Map(vn30Data.map(d => [d.tradingDate, d.close]));
  const aligned = [];

  for (let i = 0; i < stockData.length; i++) {
    const date = stockData[i].tradingDate;
    const stockPrice = stockData[i].close;
    const vn30Price = vn30Map.get(date);

    if (vn30Price) {
      aligned.push({ date, stock: stockPrice, vn30: vn30Price });
    }
  }

  if (aligned.length < 5) {
    return { beta: 1.0, directionalAccuracy: 0.5, peerCorrelations: [] };
  }

  // Calculate log returns
  const retStock = [];
  const retVN30 = [];
  for (let i = 1; i < aligned.length; i++) {
    retStock.push(Math.log(aligned[i].stock / aligned[i - 1].stock));
    retVN30.push(Math.log(aligned[i].vn30 / aligned[i - 1].vn30));
  }

  // Calculate Beta
  const N = retStock.length;
  const meanStock = retStock.reduce((s, v) => s + v, 0) / N;
  const meanVN30 = retVN30.reduce((s, v) => s + v, 0) / N;

  let cov = 0;
  let varVN30 = 0;
  for (let i = 0; i < N; i++) {
    cov += (retStock[i] - meanStock) * (retVN30[i] - meanVN30);
    varVN30 += Math.pow(retVN30[i] - meanVN30, 2);
  }
  cov = cov / (N - 1);
  varVN30 = varVN30 / (N - 1);

  const beta = varVN30 !== 0 ? cov / varVN30 : 1.0;

  // Directional Accuracy
  let matchingSigns = 0;
  for (let i = 0; i < N; i++) {
    if (Math.sign(retStock[i]) === Math.sign(retVN30[i])) {
      matchingSigns++;
    }
  }
  const directionalAccuracy = matchingSigns / N;

  // Pearson Correlation vs Peer Stocks
  const peerCorrelations = [];
  for (const peerSymbol of Object.keys(allStocks)) {
    if (peerSymbol === stockData[0].symbol) continue;

    const peerData = allStocks[peerSymbol];
    const peerMap = new Map(peerData.map(d => [d.tradingDate, d.close]));
    
    const peerAligned = [];
    for (let i = 0; i < stockData.length; i++) {
      const date = stockData[i].tradingDate;
      const peerPrice = peerMap.get(date);
      if (peerPrice) {
        peerAligned.push({ stock: stockData[i].close, peer: peerPrice });
      }
    }

    if (peerAligned.length < 5) continue;

    // Log returns
    const pRetStock = [];
    const pRetPeer = [];
    for (let i = 1; i < peerAligned.length; i++) {
      pRetStock.push(Math.log(peerAligned[i].stock / peerAligned[i - 1].stock));
      pRetPeer.push(Math.log(peerAligned[i].peer / peerAligned[i - 1].peer));
    }

    const pN = pRetStock.length;
    const pMeanStock = pRetStock.reduce((s, v) => s + v, 0) / pN;
    const pMeanPeer = pRetPeer.reduce((s, v) => s + v, 0) / pN;

    let pCov = 0;
    let pVarStock = 0;
    let pVarPeer = 0;

    for (let i = 0; i < pN; i++) {
      const diffS = pRetStock[i] - pMeanStock;
      const diffP = pRetPeer[i] - pMeanPeer;
      pCov += diffS * diffP;
      pVarStock += Math.pow(diffS, 2);
      pVarPeer += Math.pow(diffP, 2);
    }

    const r = pCov / Math.sqrt(pVarStock * pVarPeer);
    peerCorrelations.push({
      symbol: peerSymbol,
      r: isNaN(r) ? 0.0 : r
    });
  }

  return { beta, directionalAccuracy, peerCorrelations };
}

// Main execution block
async function main() {
  console.log('--- STARTING NODE PIPELINE SYNC ---');

  const today = new Date();
  const todayStr = `${today.getDate().toString().padStart(2, '0')}/${(today.getMonth() + 1).toString().padStart(2, '0')}/${today.getFullYear()}`;

  // 1. Fetch VN30 Index Data
  const vn30Data = await fetchStockData(INDEX_SYMBOL, START_DATE, todayStr);
  if (!vn30Data) {
    console.error('CRITICAL ERROR: Failed to fetch VN30 index data.');
    process.exit(1);
  }

  // Save VN30 raw data
  fs.writeFileSync(
    path.join(DATA_FOLDER, `${INDEX_SYMBOL}_processed.json`),
    JSON.stringify(vn30Data, null, 2)
  );

  // 2. Fetch Stock Tick Data (VIC, VRE, and standard peers for correlations)
  const allStocks = {};
  const targetSymbols = [...new Set([...SYMBOLS, ...PEER_SYMBOLS])];

  for (const symbol of targetSymbols) {
    const rawData = await fetchStockData(symbol, START_DATE, todayStr);
    if (rawData) {
      // Calculate volatilities
      const prices = rawData.map(d => d.close);
      const hv22 = calculateHV(prices, 22);
      const hv66 = calculateHV(prices, 66);
      const hv132 = calculateHV(prices, 132);
      const hv252 = calculateHV(prices, 252);

      const processedData = rawData.map((d, idx) => ({
        ...d,
        symbol,
        hv_22: hv22[idx],
        hv_66: hv66[idx],
        hv_132: hv132[idx],
        hv_252: hv252[idx]
      })).filter(d => d.hv_22 !== null); // Drop rows where smallest HV can't be calculated

      allStocks[symbol] = processedData;

      // Save individual processed files
      fs.writeFileSync(
        path.join(DATA_FOLDER, `${symbol}_processed.json`),
        JSON.stringify(processedData, null, 2)
      );
      console.log(`  [OK] Processed and saved ${processedData.length} records for ${symbol}`);
    }
    await sleep(100);
  }

  // 3. Build summary metrics for the target symbols
  const summary = {
    availableSymbols: SYMBOLS,
    lastUpdated: new Date().toISOString(),
    stocks: {}
  };

  for (const symbol of SYMBOLS) {
    const stockData = allStocks[symbol];
    if (!stockData || stockData.length === 0) continue;

    const latestRow = stockData[stockData.length - 1];
    
    // Compute cone
    const cone = calculateVolatilityCone(stockData);

    // Compute stats & correlations
    const { beta, directionalAccuracy, peerCorrelations } = calculateCorrelationsAndBeta(stockData, vn30Data, allStocks);

    // Compute changes (delta from mean)
    const mean = (arr) => arr.reduce((s, v) => s + v, 0) / arr.length;
    
    const extractHVField = (field) => stockData.map(d => d[field]).filter(v => v !== null).map(v => v * 100);
    const hv22Vals = extractHVField('hv_22');
    const hv66Vals = extractHVField('hv_66');
    const hv132Vals = extractHVField('hv_132');
    const hv252Vals = extractHVField('hv_252');

    const computeChange = (current, values) => {
      const avg = mean(values);
      return current - avg;
    };

    summary.stocks[symbol] = {
      symbol,
      latestDate: latestRow.tradingDate,
      currentPrice: latestRow.close,
      beta,
      directionalAccuracy,
      peerCorrelations,
      volatilityCone: cone,
      hv_metrics: {
        'HV 22 (1M)': {
          current: latestRow.hv_22 * 100,
          mean: mean(hv22Vals),
          min: Math.min(...hv22Vals),
          max: Math.max(...hv22Vals),
          delta: computeChange(latestRow.hv_22 * 100, hv22Vals)
        },
        'HV 66 (3M)': {
          current: latestRow.hv_66 * 100,
          mean: mean(hv66Vals),
          min: Math.min(...hv66Vals),
          max: Math.max(...hv66Vals),
          delta: computeChange(latestRow.hv_66 * 100, hv66Vals)
        },
        'HV 132 (6M)': {
          current: latestRow.hv_132 * 100,
          mean: mean(hv132Vals),
          min: Math.min(...hv132Vals),
          max: Math.max(...hv132Vals),
          delta: computeChange(latestRow.hv_132 * 100, hv132Vals)
        },
        'HV 252 (1Y)': {
          current: latestRow.hv_252 * 100,
          mean: mean(hv252Vals),
          min: Math.min(...hv252Vals),
          max: Math.max(...hv252Vals),
          delta: computeChange(latestRow.hv_252 * 100, hv252Vals)
        }
      }
    };
  }

  // Save summary.json
  fs.writeFileSync(
    path.join(DATA_FOLDER, 'summary.json'),
    JSON.stringify(summary, null, 2)
  );

  console.log('\n[SUCCESS] Node data pipeline sync completed successfully.');
}

main().catch(console.error);
