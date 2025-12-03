# Backtest Output Directory

This directory contains backtest results and reports.

## Generated Files

When you run the backtest system, the following files will be created:

- `backtest_signals.csv` - Historical signals detected over 5 years
- `backtest_results.csv` - Trade simulation results with P&L
- `reports/` - Directory containing analysis reports:
  - `summary_report.csv` - Overall performance summary
  - `timeframe_report.csv` - Performance breakdown by timeframe
  - `type_report.csv` - Performance breakdown by divergence type
  - `quarterly_report.csv` - Quarterly performance data
  - `trade_details_report.csv` - Detailed information for each trade
  - `equity_curve.csv` - Cumulative P&L over time

## Running the Backtest

To run the complete backtest system:

```bash
python run_backtest.py
```

To test the system with limited data:

```bash
python test_backtest.py
```

See `run_backtest.py --help` for more options.
