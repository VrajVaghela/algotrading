"""
API Server Module
Flask REST API for backtesting service and frontend.
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
from pathlib import Path
import traceback

from .data_loader import DataLoader, load_sample_data
from .strategy import get_strategy, MACrossoverRSIStrategy
from .backtest_engine import run_backtest
from .performance import calculate_metrics, metrics_to_dict, PerformanceAnalyzer


# Initialize Flask app
app = Flask(__name__, static_folder='../frontend')
CORS(app)

# Global data cache
_data_cache = None
_uploaded_file_path = None


def get_data():
    """Load and cache market data."""
    global _data_cache
    
    global _data_cache, _uploaded_file_path
    
    if _data_cache is not None:
        return _data_cache
    
    # Check for uploaded file first
    project_root = Path(__file__).parent.parent
    loader = DataLoader(str(project_root))
    
    if _uploaded_file_path and os.path.exists(_uploaded_file_path):
        try:
            print(f"Loading uploaded data from {_uploaded_file_path}")
            _data_cache = loader.load_csv(_uploaded_file_path)
            # Validate
            loader.validate_ohlcv(_data_cache)
            return _data_cache
        except Exception as e:
            print(f"Error loading uploaded file: {e}")
            _data_cache = None # Fallback to other methods
    
    # Try to load from available data files
    
    # Check for data files
    zip_files = list(project_root.glob('*.zip'))
    excel_files = list(project_root.glob('*.xlsx'))
    csv_files = list(project_root.glob('*.csv'))
    
    try:
        if excel_files:
            # Load Excel file
            _data_cache = loader.load_excel(str(excel_files[0]))
            print(f"Loaded data from {excel_files[0].name}")
        elif zip_files:
            # Load from ZIP
            _data_cache = loader.load_from_zip(str(zip_files[0]))
            print(f"Loaded data from {zip_files[0].name}")
        elif csv_files:
            # Load CSV
            _data_cache = loader.load_csv(str(csv_files[0]))
            print(f"Loaded data from {csv_files[0].name}")
        else:
            # Use sample data
            print("No data files found, using synthetic sample data")
            _data_cache = load_sample_data()
        
        # Validate data
        loader.validate_ohlcv(_data_cache)
        
    except Exception as e:
        print(f"Error loading data: {e}")
        print("Falling back to sample data")
        _data_cache = load_sample_data()
    
    return _data_cache


@app.route('/')
def serve_frontend():
    """Serve the frontend HTML."""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    """Serve static files."""
    return send_from_directory(app.static_folder, path)


@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'message': 'Algo Trading API is running'})


@app.route('/api/upload', methods=['POST'])
def api_upload_file():
    """Handle CSV file upload."""
    global _data_cache, _uploaded_file_path
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'}), 400
        
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'}), 400
        
    if file and file.filename.endswith('.csv'):
        try:
            # Save file to uploads directory
            project_root = Path(__file__).parent.parent
            uploads_dir = project_root / 'uploads'
            uploads_dir.mkdir(exist_ok=True)
            
            filename = "uploaded_data.csv" # Fixed name to simplify
            filepath = uploads_dir / filename
            file.save(str(filepath))
            
            # Reset cache and set uploaded path
            _data_cache = None
            _uploaded_file_path = str(filepath)
            
            # Reload data to verify it works
            df = get_data()
            
            return jsonify({
                'success': True, 
                'message': 'File uploaded successfully',
                'data_info': {
                    'filename': file.filename,
                    'rows': len(df),
                    'start_date': str(df['date'].min()),
                    'end_date': str(df['date'].max())
                }
            })
            
        except Exception as e:
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
            
    return jsonify({'success': False, 'error': 'Invalid file type. Please upload a CSV.'}), 400


@app.route('/api/run-backtest', methods=['POST', 'GET'])
def api_run_backtest():
    """
    Run a backtest with given parameters.
    
    Query/Body params:
        strategy: Strategy name (ma_crossover, rsi, ma_rsi, bollinger)
        fast_period: Fast MA period (default: 10)
        slow_period: Slow MA period (default: 50)
        rsi_period: RSI period (default: 14)
        rsi_oversold: RSI oversold level (default: 30)
        rsi_overbought: RSI overbought level (default: 70)
        initial_capital: Starting capital (default: 100000)
        commission: Commission rate (default: 0.001)
    """
    try:
        # Get parameters
        if request.method == 'POST':
            params = request.json or {}
        else:
            params = request.args
        
        strategy_name = params.get('strategy', 'ma_rsi')
        fast_period = int(params.get('fast_period', 10))
        slow_period = int(params.get('slow_period', 50))
        rsi_period = int(params.get('rsi_period', 14))
        rsi_oversold = int(params.get('rsi_oversold', 30))
        rsi_overbought = int(params.get('rsi_overbought', 70))
        initial_capital = float(params.get('initial_capital', 100000))
        commission = float(params.get('commission', 0.001))
        
        # Load data
        df = get_data()
        
        # Create strategy
        if strategy_name == 'ma_rsi':
            strategy = MACrossoverRSIStrategy(
                fast_period=fast_period,
                slow_period=slow_period,
                rsi_period=rsi_period,
                rsi_oversold=rsi_oversold,
                rsi_overbought=rsi_overbought
            )
        else:
            strategy_params = {
                'fast_period': fast_period,
                'slow_period': slow_period,
                'period': rsi_period,
                'oversold': rsi_oversold,
                'overbought': rsi_overbought
            }
            strategy = get_strategy(strategy_name, **strategy_params)
        
        # Run backtest
        result = run_backtest(
            df=df,
            strategy=strategy,
            initial_capital=initial_capital,
            commission=commission
        )
        
        # Calculate metrics
        metrics = calculate_metrics(result)
        
        # Get equity curve data
        equity_data = result.equity_curve[['date', 'equity']].copy()
        equity_data['date'] = equity_data['date'].astype(str)
        
        # Get drawdown data
        analyzer = PerformanceAnalyzer()
        drawdown_data = analyzer.get_drawdown_series(result.equity_curve)
        drawdown_data['date'] = drawdown_data['date'].astype(str)
        
        # Get trades data
        trades_data = [
            {
                'entry_date': str(t.entry_date),
                'entry_price': round(t.entry_price, 2),
                'exit_date': str(t.exit_date),
                'exit_price': round(t.exit_price, 2),
                'side': t.side,
                'pnl': round(t.pnl, 2),
                'pnl_percent': round(t.pnl_percent, 2),
                'duration_days': t.duration_days
            }
            for t in result.trades
        ]
        
        # Get signals with price for chart
        signals_df = result.signals_df[['date', 'close', 'signal']].copy()
        signals_df['date'] = signals_df['date'].astype(str)
        buy_signals = signals_df[signals_df['signal'] == 1][['date', 'close']].to_dict('records')
        sell_signals = signals_df[signals_df['signal'] == -1][['date', 'close']].to_dict('records')
        
        return jsonify({
            'success': True,
            'strategy': {
                'name': result.strategy_name,
                'params': result.strategy_params
            },
            'metrics': metrics_to_dict(metrics),
            'equity_curve': equity_data.to_dict('records'),
            'drawdown': drawdown_data.to_dict('records'),
            'trades': trades_data,
            'signals': {
                'buy': buy_signals,
                'sell': sell_signals
            },
            'summary': {
                'initial_capital': initial_capital,
                'final_value': round(result.final_value, 2),
                'total_return': round(result.total_return, 2),
                'total_return_pct': round(result.total_return_pct, 2)
            }
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/strategies')
def api_get_strategies():
    """Get available trading strategies."""
    strategies = [
        {
            'id': 'ma_crossover',
            'name': 'MA Crossover',
            'description': 'Buy when fast MA crosses above slow MA, sell on cross below.'
        },
        {
            'id': 'rsi',
            'name': 'RSI',
            'description': 'Buy when RSI exits oversold, sell when RSI exits overbought.'
        },
        {
            'id': 'ma_rsi',
            'name': 'MA Crossover + RSI',
            'description': 'Combined strategy using MA crossover with RSI confirmation.'
        },
        {
            'id': 'bollinger',
            'name': 'Bollinger Bands',
            'description': 'Mean reversion strategy using Bollinger Bands.'
        }
    ]
    return jsonify({'strategies': strategies})


@app.route('/api/data-info')
def api_data_info():
    """Get information about loaded data."""
    df = get_data()
    
    return jsonify({
        'rows': len(df),
        'start_date': str(df['date'].min()),
        'end_date': str(df['date'].max()),
        'columns': list(df.columns),
        'has_volume': 'volume' in df.columns
    })


def run_server(host: str = '0.0.0.0', port: int = 5000, debug: bool = True):
    """Run the Flask development server."""
    print(f"\n{'='*50}")
    print("  Algorithmic Trading Backtester")
    print(f"{'='*50}")
    print(f"\n  Server running at: http://localhost:{port}")
    print(f"  API docs: http://localhost:{port}/api/health")
    print("\n  Press Ctrl+C to stop\n")
    
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server()
