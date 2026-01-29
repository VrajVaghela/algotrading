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
    backtestForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        await runBacktest();
    });

    // RSI slider value display
    rsiPeriodSlider.addEventListener('input', (e) => {
        rsiPeriodValue.textContent = e.target.value;
    });

    // File selection
    csvUpload.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            fileName.textContent = file.name;
            uploadBtn.disabled = false;
        } else {
            fileName.textContent = 'Select CSV File';
            uploadBtn.disabled = true;
        }
    });

    // Upload button
    uploadBtn.addEventListener('click', async () => {
        await uploadData();
    });
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
    const equityCtx = document.getElementById('equityChart').getContext('2d');
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

    // Drawdown Chart
    const drawdownCtx = document.getElementById('drawdownChart').getContext('2d');
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

        // Update UI with results
        updateMetrics(data.metrics, data.summary);
        updateCharts(data.equity_curve, data.drawdown);
        updateTradesTable(data.trades);

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
