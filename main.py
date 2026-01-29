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
from src.data_loader import load_sample_data
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
    print(f"      Loaded {len(df)} bars from {df['date'].min().date()} to {df['date'].max().date()}")
    
    # Create strategy
    print(f"\n[2/4] Creating strategy: {args.strategy}")
    print(f"\n[2/4] Creating strategy: {args.strategy}")
    
    # Filter args to pass relevant ones to strategy
    # Convert args namespace to dict, strategy classes will ignore unused kwargs
    strategy_params = vars(args)
    
    strategy = get_strategy(args.strategy, **strategy_params)
    print(f"      Parameters: {strategy.get_params()}")
    
    # Run backtest
    print(f"\n[3/4] Running backtest with ₹{args.capital:,.0f} capital...")
    result = run_backtest(
        df=df,
        strategy=strategy,
        initial_capital=args.capital,
        commission=args.commission
    )
    
    # Calculate metrics
    print("\n[4/4] Calculating performance metrics...")
    metrics = calculate_metrics(result)
    
    # Print results
    print("\n" + "="*60)
    print("  BACKTEST RESULTS")
    print("="*60)
    
    print(f"""
╔════════════════════════════════════════════════════════════╗
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
                          choices=['ma_crossover', 'rsi', 'ma_rsi', 'bollinger', 'macd', 'vwap', 'bollinger_rsi'],
                          help='Trading strategy')
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
