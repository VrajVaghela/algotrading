/**
 * AlgoTrader Dashboard - Frontend Application
 * Handles API communication and chart rendering
 */

// API Configuration
const API_BASE = window.location.origin;

// Chart instances
let equityChart = null;
let drawdownChart = null;

// DOM Elements
const backtestForm = document.getElementById('backtestForm');
const runBtn = document.getElementById('runBtn');
const loadingOverlay = document.getElementById('loadingOverlay');
const rsiPeriodSlider = document.getElementById('rsiPeriod');
const rsiPeriodValue = document.getElementById('rsiPeriodValue');
const csvUpload = document.getElementById('csvUpload');
const uploadBtn = document.getElementById('uploadBtn');
const fileName = document.getElementById('fileName');
const uploadStatus = document.getElementById('uploadStatus');

// Initialize application
document.addEventListener('DOMContentLoaded', () => {
    initializeForm();
    initializeCharts();
});

/**
 * Initialize form event handlers
 */
function initializeForm() {
    // Form submission
    if (backtestForm) {
        backtestForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await runBacktest();
        });
    }

    // RSI slider value display
    if (rsiPeriodSlider) {
        rsiPeriodSlider.addEventListener('input', (e) => {
            rsiPeriodValue.textContent = e.target.value;
        });
    }

    // File selection
    if (csvUpload) {
        const dropZone = document.getElementById('dropZone');

        // Standard input change
        csvUpload.addEventListener('change', (e) => {
            handleFileSelect(e.target.files[0]);
        });

        // Drag and drop events
        if (dropZone) {
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                dropZone.addEventListener(eventName, preventDefaults, false);
            });

            ['dragenter', 'dragover'].forEach(eventName => {
                dropZone.addEventListener(eventName, highlight, false);
            });

            ['dragleave', 'drop'].forEach(eventName => {
                dropZone.addEventListener(eventName, unhighlight, false);
            });

            dropZone.addEventListener('drop', handleDrop, false);
        }
    }

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight(e) {
        document.getElementById('dropZone').classList.add('drag-over');
    }

    function unhighlight(e) {
        document.getElementById('dropZone').classList.remove('drag-over');
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFileSelect(files[0]);
    }

    function handleFileSelect(file) {
        if (file) {
            fileName.textContent = file.name;
            fileName.classList.add('selected-file-name');
            uploadBtn.disabled = false;
            // Update input files if came from drop
            if (csvUpload.files[0] !== file) {
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                csvUpload.files = dataTransfer.files;
            }
        } else {
            fileName.textContent = 'Select CSV File';
            fileName.classList.remove('selected-file-name');
            uploadBtn.disabled = true;
        }
    }

    // Upload button
    if (uploadBtn) {
        uploadBtn.addEventListener('click', async () => {
            await uploadData();
        });
    }
}

/**
 * Initialize empty charts
 */
function initializeCharts() {
    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
            mode: 'index',
            intersect: false,
        },
        plugins: {
            legend: {
                display: false
            },
            tooltip: {
                backgroundColor: 'rgba(17, 24, 39, 0.95)',
                titleColor: '#f0f4f8',
                bodyColor: '#94a3b8',
                borderColor: 'rgba(255, 255, 255, 0.1)',
                borderWidth: 1,
                cornerRadius: 8,
                padding: 12,
                displayColors: false
            }
        },
        scales: {
            x: {
                grid: {
                    color: 'rgba(255, 255, 255, 0.05)',
                    drawBorder: false
                },
                ticks: {
                    color: '#64748b',
                    maxTicksLimit: 8
                }
            },
            y: {
                grid: {
                    color: 'rgba(255, 255, 255, 0.05)',
                    drawBorder: false
                },
                ticks: {
                    color: '#64748b',
                    callback: function (value) {
                        return '₹' + value.toLocaleString();
                    }
                }
            }
        }
    };

    // Equity Chart
    const equityCanvas = document.getElementById('equityChart');
    if (equityCanvas) {
        const equityCtx = equityCanvas.getContext('2d');
        equityChart = new Chart(equityCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Portfolio Value',
                    data: [],
                    borderColor: '#3b82f6',
                    backgroundColor: createGradient(equityCtx, '#3b82f6'),
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    pointHoverBackgroundColor: '#3b82f6'
                }]
            },
            options: chartOptions
        });
    }

    // Drawdown Chart
    const drawdownCanvas = document.getElementById('drawdownChart');
    if (drawdownCanvas) {
        const drawdownCtx = drawdownCanvas.getContext('2d');
        const drawdownOptions = { ...chartOptions };
        drawdownOptions.scales = {
            ...chartOptions.scales,
            y: {
                ...chartOptions.scales.y,
                ticks: {
                    color: '#64748b',
                    callback: function (value) {
                        return value.toFixed(1) + '%';
                    }
                }
            }
        };

        drawdownChart = new Chart(drawdownCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Drawdown',
                    data: [],
                    borderColor: '#ef4444',
                    backgroundColor: createGradient(drawdownCtx, '#ef4444'),
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    pointHoverBackgroundColor: '#ef4444'
                }]
            },
            options: drawdownOptions
        });
    }
}

/**
 * Create gradient for chart backgrounds
 */
function createGradient(ctx, color) {
    const gradient = ctx.createLinearGradient(0, 0, 0, 280);
    gradient.addColorStop(0, color + '40');
    gradient.addColorStop(1, color + '00');
    return gradient;
}

/**
 * Run backtest with current form parameters
 */
/**
 * Run backtest with current form parameters
 */
async function runBacktest() {
    // Show loading state
    setLoading(true);

    try {
        // Collect form data
        const formData = new FormData(backtestForm);
        const params = {};

        formData.forEach((value, key) => {
            params[key] = value;
        });

        // Convert commission from percentage to decimal
        params.commission = parseFloat(params.commission) / 100;

        // Make API request
        const response = await fetch(`${API_BASE}/api/run-backtest`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(params)
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Backtest failed');
        }

        // Save data for detailed chart
        // Save data for detailed chart - MOVED TO SERVER CACHE
        // localStorage.setItem('backtestData', JSON.stringify(data));

        // Update UI with results
        updateMetrics(data.metrics, data.summary);
        updateCharts(data.equity_curve, data.drawdown);
        updateTradesTable(data.trades);

        // Show detailed graph button if it exists
        const viewGraphBtn = document.getElementById('viewGraphBtn');
        if (viewGraphBtn) {
            viewGraphBtn.style.display = 'inline-flex';
        }

    } catch (error) {
        console.error('Backtest error:', error);
        alert('Error running backtest: ' + error.message);
    } finally {
        setLoading(false);
    }
}

/**
 * Upload CSV data
 */
async function uploadData() {
    const file = csvUpload.files[0];
    if (!file) return;

    // Show uploading state
    uploadBtn.innerHTML = '<span class="btn-loader"></span> Uploading...';
    uploadBtn.disabled = true;

    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_BASE}/api/upload`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Upload failed');
        }

        // Success
        uploadStatus.textContent = `Using: ${data.data_info.filename}`;
        uploadStatus.classList.add('success');

        // Trigger backtest to refresh view with new data
        // We can pass a flag or just let runBacktest use the updated backend state
        await runBacktest();

        alert('Data uploaded successfully!');

    } catch (error) {
        console.error('Upload error:', error);
        alert('Error uploading data: ' + error.message);
        uploadStatus.textContent = 'Upload failed';
        uploadStatus.classList.add('error');
    } finally {
        uploadBtn.innerHTML = 'Upload Data';
        uploadBtn.disabled = false;
    }
}

/**
 * Update metrics display
 */
function updateMetrics(metrics, summary) {
    // Total Return
    const totalReturn = document.getElementById('totalReturn');
    const totalReturnPct = document.getElementById('totalReturnPct');

    totalReturn.textContent = formatCurrency(summary.total_return);
    totalReturnPct.textContent = formatPercentage(summary.total_return_pct);
    totalReturnPct.className = 'metric-sub ' + (summary.total_return_pct >= 0 ? 'positive' : 'negative');

    // Sharpe Ratio
    document.getElementById('sharpeRatio').textContent = metrics.risk.sharpe_ratio.toFixed(2);

    // Max Drawdown
    document.getElementById('maxDrawdown').textContent = formatPercentage(metrics.risk.max_drawdown_pct);

    // Win Rate
    document.getElementById('winRate').textContent = formatPercentage(metrics.trades.win_rate);

    // Total Trades
    document.getElementById('totalTrades').textContent = metrics.trades.total_trades;

    // Profit Factor
    const pf = metrics.trades.profit_factor;
    document.getElementById('profitFactor').textContent = pf === Infinity ? '∞' : pf.toFixed(2);
}

/**
 * Update charts with new data
 */
function updateCharts(equityCurve, drawdown) {
    // Prepare data
    const labels = equityCurve.map(d => formatDate(d.date));
    const equityData = equityCurve.map(d => d.equity);
    const drawdownData = drawdown.map(d => d.drawdown_pct);

    // Update Equity Chart
    equityChart.data.labels = labels;
    equityChart.data.datasets[0].data = equityData;
    equityChart.update('none');

    // Update Drawdown Chart
    drawdownChart.data.labels = labels;
    drawdownChart.data.datasets[0].data = drawdownData;
    drawdownChart.update('none');
}

/**
 * Render detailed chart with indicators and signals
 */
/**
 * Render interactive trading chart using Lightweight Charts
 */
function renderTradingChart(data) {
    const container = document.getElementById('chartContainer');
    // Clear previous
    container.innerHTML = '';

    // Create Chart
    const chart = LightweightCharts.createChart(container, {
        layout: {
            background: { type: 'solid', color: '#0f172a' },
            textColor: '#94a3b8',
        },
        grid: {
            vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
            horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
        },
        rightPriceScale: {
            borderColor: 'rgba(255, 255, 255, 0.1)',
        },
        leftPriceScale: {
            visible: true,
            borderColor: 'rgba(255, 255, 255, 0.1)',
        },
        timeScale: {
            borderColor: 'rgba(255, 255, 255, 0.1)',
            timeVisible: true,
        },
    });

    // Handle resizing
    window.addEventListener('resize', () => {
        chart.resize(container.clientWidth, container.clientHeight);
    });

    // 1. Candlestick Series (OHLC)
    // Map data to LWC format
    // data.ohlc contains { time (unix), open, high, low, close }
    const candleData = data.ohlc.map(d => ({
        time: d.time + 19800, // Shift for IST (UTC+5:30) if desired, or just use d.time for UTC. Let's keep IST shift for now as requested context implies Indian user.
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
    }));

    // Sort items by time to prevent LWC errors
    candleData.sort((a, b) => a.time - b.time);

    // Remove duplicates if any
    const uniqueCandleData = [];
    let lastTime = null;
    for (const item of candleData) {
        if (item.time !== lastTime) {
            uniqueCandleData.push(item);
            lastTime = item.time;
        }
    }

    const mainSeries = chart.addCandlestickSeries({
        upColor: '#10b981',
        downColor: '#ef4444',
        borderVisible: false,
        wickUpColor: '#10b981',
        wickDownColor: '#ef4444',
    });

    mainSeries.setData(uniqueCandleData);

    // 2. Indicators
    const indicators = data.indicators || {};
    const colors = ['#f59e0b', '#8b5cf6', '#3b82f6', '#ec4899', '#14b8a6'];
    let colorIdx = 0;

    const overlaySeriesMap = new Map(); // name -> series

    const overlaysList = document.getElementById('overlaysList');
    overlaysList.innerHTML = ''; // Clear list

    Object.keys(indicators).forEach(key => {
        // Skip if data is empty or all null
        if (!indicators[key] || indicators[key].length === 0) return;

        // Determine series type
        let series;
        let color = colors[colorIdx % colors.length];

        let label = key.replace(/_/g, ' ').toUpperCase();

        // BB logic: Upper/Lower usually share color
        if (key === 'bb_upper' || key === 'bb_lower') {
            color = 'rgba(16, 185, 129, 0.5)';
            label = key === 'bb_upper' ? 'BB Upper' : 'BB Lower';
        }

        const oscillators = ['rsi', 'adx'];
        const isOscillator = oscillators.includes(key);

        series = chart.addLineSeries({
            color: color,
            lineWidth: 1,
            title: label,
            priceScaleId: isOscillator ? 'left' : 'right',
        });

        const lineData = data.dates.map((ts, i) => ({
            time: ts + 19800,
            value: indicators[key][i]
        })).filter(d => d.value !== null && d.value !== undefined) // Filter nulls
            .sort((a, b) => a.time - b.time);

        // Remove duplicates for lineData
        const uniqueLineData = [];
        let lastLineTime = null;
        for (const item of lineData) {
            if (item.time !== lastLineTime) {
                uniqueLineData.push(item);
                lastLineTime = item.time;
            }
        }

        series.setData(uniqueLineData);

        // Store for toggling
        overlaySeriesMap.set(key, series);

        if (key !== 'bb_upper' && key !== 'bb_lower') {
            colorIdx++;
        }

        // Add Toggle UI
        const toggleItem = document.createElement('label');
        toggleItem.className = 'toggle-item';
        toggleItem.innerHTML = `
            <span class="toggle-label">
                <span class="color-dot" style="background-color: ${color};"></span>
                ${label}
            </span>
            <input type="checkbox" class="toggle-checkbox" checked data-key="${key}">
        `;

        // Event listener
        toggleItem.querySelector('input').addEventListener('change', (e) => {
            const isVisible = e.target.checked;
            series.applyOptions({ visible: isVisible });
        });

        overlaysList.appendChild(toggleItem);
    });

    // 3. Markers (Buy/Sell)
    const markers = [];

    try {
        // Process Buy Signals
        if (data.signals.buy) {
            data.signals.buy.forEach(sig => {
                // Backend now sends timestamps (floats) or strings. Handle both.
                let timeVal = sig.date;
                if (typeof timeVal === 'string') {
                    // Fallback if backend not updated or cached data
                    timeVal = new Date(timeVal).getTime() / 1000;
                }

                if (!isNaN(timeVal)) {
                    markers.push({
                        time: timeVal + 19800,
                        position: 'belowBar',
                        color: '#10b981',
                        shape: 'arrowUp',
                        text: 'BUY',
                    });
                }
            });
        }

        // Process Sell Signals
        if (data.signals.sell) {
            data.signals.sell.forEach(sig => {
                let timeVal = sig.date;
                if (typeof timeVal === 'string') {
                    timeVal = new Date(timeVal).getTime() / 1000;
                }

                if (!isNaN(timeVal)) {
                    markers.push({
                        time: timeVal + 19800,
                        position: 'aboveBar',
                        color: '#ef4444',
                        shape: 'arrowDown',
                        text: 'SELL',
                    });
                }
            });
        }

        // Sort markers by time
        markers.sort((a, b) => a.time - b.time);
        mainSeries.setMarkers(markers);

    } catch (err) {
        console.error("Error setting markers:", err);
    }

    // Toggle Markers
    const toggleBuy = document.getElementById('toggleBuy');
    const toggleSell = document.getElementById('toggleSell');

    const updateMarkers = () => {
        const activeMarkers = markers.filter(m => {
            if (m.text === 'BUY' && !toggleBuy.checked) return false;
            if (m.text === 'SELL' && !toggleSell.checked) return false;
            return true;
        });
        mainSeries.setMarkers(activeMarkers);
    };

    if (toggleBuy) toggleBuy.addEventListener('change', updateMarkers);
    if (toggleSell) toggleSell.addEventListener('change', updateMarkers);

    // Fit content
    try {
        chart.timeScale().fitContent();
    } catch (e) {
        console.warn("Fit content failed:", e);
    }
}


/**
 * Update trades table
 */
function updateTradesTable(trades) {
    const tbody = document.getElementById('tradesTableBody');
    const tradesCount = document.getElementById('tradesCount');

    tradesCount.textContent = `${trades.length} trades`;

    if (trades.length === 0) {
        tbody.innerHTML = `
            <tr class="empty-row">
                <td colspan="8">No trades executed</td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = trades.map(trade => `
        <tr>
            <td>${formatDate(trade.entry_date)}</td>
            <td>${formatCurrency(trade.entry_price)}</td>
            <td>${formatDate(trade.exit_date)}</td>
            <td>${formatCurrency(trade.exit_price)}</td>
            <td><span class="trade-side ${trade.side.toLowerCase()}">${trade.side}</span></td>
            <td class="${trade.pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}">${formatCurrency(trade.pnl)}</td>
            <td class="${trade.pnl_percent >= 0 ? 'pnl-positive' : 'pnl-negative'}">${formatPercentage(trade.pnl_percent)}</td>
            <td>${trade.duration_days}d</td>
        </tr>
    `).join('');
}

/**
 * Set loading state
 */
function setLoading(isLoading) {
    if (isLoading) {
        runBtn.classList.add('loading');
        loadingOverlay.classList.add('active');
    } else {
        runBtn.classList.remove('loading');
        loadingOverlay.classList.remove('active');
    }
}

/**
 * Format currency
 */
function formatCurrency(value) {
    const abs = Math.abs(value);
    const formatted = abs >= 1000
        ? '₹' + (abs / 1000).toFixed(1) + 'K'
        : '₹' + abs.toFixed(0);
    return value < 0 ? '-' + formatted : formatted;
}

/**
 * Format percentage
 */
function formatPercentage(value) {
    const sign = value >= 0 ? '+' : '';
    return sign + value.toFixed(2) + '%';
}

/**
 * Format date
 */
function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: '2-digit'
    });
}
