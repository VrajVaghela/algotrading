"""
Algorithmic Trading Backtester
Main entry point for running the application.
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.api_server import run_server
from src.data_loader import load_sample_data, DataLoader
from src.strategy import MACrossoverRSIStrategy, get_strategy
from src.backtest_engine import run_backtest
from src.performance import calculate_metrics, PerformanceAnalyzer


def run_cli_backtest(args):
    """Run backtest from command line."""
    print("\n" + "="*60)
    print("  ALGORITHMIC TRADING BACKTESTER")
    print("="*60 + "\n")
    
    # Load data
    print("[1/4] Loading market data...")
    df = load_sample_data()
    
    # Detect timeframe
    loader = DataLoader()
    timeframe = loader.detect_timeframe(df)
    print(f"      Loaded {len(df)} bars from {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"      Detected timeframe: {timeframe}")
    
    strategies_to_run = []
    if args.strategy == 'all':
        strategies_to_run = [
            'high_sharpe', 'ma_crossover', 'rsi', 'ma_rsi', 
            'bollinger', 'bollinger_rsi', 'macd', 'vwap', 'dynamic_regime'
        ]
    else:
        strategies_to_run = [args.strategy]

    results = []

    print(f"\n[2/4] Running backtest(s) for: {', '.join(strategies_to_run)}")
    
    for str_name in strategies_to_run:
        print(f"\n  --- Strategy: {str_name} ---")
        
        # Filter args to pass relevant ones to strategy
        strategy_params = vars(args)
        strategy_params['data_timeframe'] = timeframe
        
        try:
            strategy = get_strategy(str_name, **strategy_params)
            # print(f"      Parameters: {strategy.get_params()}")
            
            # Run backtest
            result = run_backtest(
                df=df,
                strategy=strategy,
                initial_capital=args.capital,
                commission=args.commission
            )
            
            metrics = calculate_metrics(result)
            results.append({
                'name': str_name,
                'result': result,
                'metrics': metrics
            })
            print(f"      Total Return: {result.total_return_pct:+.2f}% | Sharpe: {metrics.sharpe_ratio:.2f}")

        except Exception as e:
            print(f"      FAILED: {e}")

    # Print Report
    if len(results) == 1:
        # Detailed single report (original behavior)
        r = results[0]
        result = r['result']
        metrics = r['metrics']
        
        print("\n" + "="*60)
        print("  BACKTEST RESULTS")
        print("="*60)
        
        print(f"""
╔════════════════════════════════════════════════════════════╗
║  STRATEGY: {r['name'].upper():<40}║
╠════════════════════════════════════════════════════════════╣
║  RETURNS                                                    ║
╠════════════════════════════════════════════════════════════╣
║  Initial Capital:    ₹{args.capital:>12,.2f}                    ║
║  Final Value:        ₹{result.final_value:>12,.2f}                    ║
║  Total Return:       ₹{result.total_return:>12,.2f} ({result.total_return_pct:>+.2f}%)          ║
║  Annualized Return:   {metrics.annualized_return:>11.2f}%                         ║
╠════════════════════════════════════════════════════════════╣
║  RISK METRICS                                               ║
╠════════════════════════════════════════════════════════════╣
║  Sharpe Ratio:        {metrics.sharpe_ratio:>11.2f}                          ║
║  Sortino Ratio:       {metrics.sortino_ratio:>11.2f}                          ║
║  Max Drawdown:        {metrics.max_drawdown_pct:>11.2f}%                         ║
║  Volatility:          {metrics.volatility:>11.2f}%                         ║
╠════════════════════════════════════════════════════════════╣
║  TRADE STATISTICS                                           ║
╠════════════════════════════════════════════════════════════╣
║  Total Trades:        {metrics.total_trades:>11}                          ║
║  Win Rate:            {metrics.win_rate:>11.2f}%                         ║
║  Profit Factor:       {metrics.profit_factor:>11.2f}                          ║
║  Avg Win:            ₹{metrics.avg_win:>11,.2f}                         ║
║  Avg Loss:           ₹{metrics.avg_loss:>11,.2f}                         ║
╚════════════════════════════════════════════════════════════╝
        """)
        
    else:
        # Comparison Table
        print("\n" + "="*95)
        print(f"  STRATEGY COMPARISON ({len(results)} strategies)")
        print("="*95)
        print(f"{'STRATEGY':<20} | {'RETURN %':<10} | {'SHARPE':<8} | {'MAX DD %':<10} | {'TRADES':<8} | {'WIN RATE %':<10}")
        print("-" * 95)
        
        # Sort by Sharpe Ratio descending
        results.sort(key=lambda x: x['metrics'].sharpe_ratio, reverse=True)
        
        for r in results:
            m = r['metrics']
            res = r['result']
            print(f"{r['name']:<20} | {res.total_return_pct:>9.2f}% | {m.sharpe_ratio:>8.2f} | {m.max_drawdown_pct:>9.2f}% | {m.total_trades:>8} | {m.win_rate:>9.2f}%")
        print("-" * 95)
        
    print("\n  Run 'python main.py serve' to start the web dashboard\n")


def main():
    parser = argparse.ArgumentParser(description='Algorithmic Trading Backtester')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Serve command
    serve_parser = subparsers.add_parser('serve', help='Start web server')
    serve_parser.add_argument('--port', type=int, default=5000, help='Port number')
    serve_parser.add_argument('--host', default='0.0.0.0', help='Host address')
    
    # Backtest command
    bt_parser = subparsers.add_parser('backtest', help='Run CLI backtest')
    bt_parser.add_argument('--strategy', default='ma_rsi', 
                          choices=['all', 'ma_crossover', 'rsi', 'ma_rsi', 'bollinger', 'macd', 'vwap', 'bollinger_rsi', 'high_sharpe', 'dynamic_regime'],
                          help='Trading strategy (use "all" to run everyone)')
    bt_parser.add_argument('--capital', type=float, default=100000, 
                          help='Initial capital')
    bt_parser.add_argument('--fast-period', type=int, default=10, 
                          help='Fast MA period')
    bt_parser.add_argument('--slow-period', type=int, default=50, 
                          help='Slow MA period')
    bt_parser.add_argument('--rsi-period', type=int, default=14, 
                          help='RSI period')
    bt_parser.add_argument('--rsi-oversold', type=int, default=30, 
                          help='RSI oversold threshold')
    bt_parser.add_argument('--rsi-overbought', type=int, default=70, 
                          help='RSI overbought threshold')
    bt_parser.add_argument('--commission', type=float, default=0.001, 
                          help='Commission rate')
    bt_parser.add_argument('--signal-period', type=int, default=9,
                          help='MACD Signal period')
    bt_parser.add_argument('--std-dev', type=float, default=2.0,
                          help='Bollinger std dev')
    bt_parser.add_argument('--adx-period', type=int, default=14,
                          help='ADX period for Dynamic Regime')
    bt_parser.add_argument('--adx-threshold', type=int, default=25,
                          help='ADX threshold for regime switch')
    
    args = parser.parse_args()
    
    if args.command == 'serve':
        run_server(host=args.host, port=args.port)
    elif args.command == 'backtest':
        run_cli_backtest(args)
    else:
        # Default: show help and run serve
        parser.print_help()
        print("\n" + "-"*50)
        print("Starting web server on port 5000...")
        print("-"*50 + "\n")
        run_server()


if __name__ == '__main__':
    main()
