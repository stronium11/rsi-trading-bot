# RSI Trading Bot - Reporting System

This document explains how to generate and use the trading bot reports.

## Overview

The reporting system exports three types of reports:

1. **Signals Report** - All RSI divergence signals detected by the scanner
2. **Trades Report** - All executed trades with P&L details
3. **Analytics Report** - Comprehensive performance analytics

## Generating Reports

### Option 1: Generate All Reports at Once

```bash
cd ~/trading_bot/rsi_trading_bot
source venv/bin/activate
python reporting.py
```

This will create three CSV files in the `reports/` directory:
- `signals_YYYYMMDD_HHMMSS.csv`
- `trades_YYYYMMDD_HHMMSS.csv`
- `analytics_YYYYMMDD_HHMMSS.csv`

### Option 2: Generate Individual Reports

```python
from reporting import TradingReporter

reporter = TradingReporter()

# Generate individual reports
reporter.export_signals_csv()     # Signals only
reporter.export_trades_csv()      # Trades only
reporter.generate_analytics()     # Analytics only
```

## Report Formats

### 1. Signals Report

**Columns:**
- `ticker` - Stock symbol
- `timeframe` - Chart timeframe (1d, 3d, 1w)
- `signal_date` - When the signal was detected
- `divergence_type` - Bullish or Bearish
- `signal_close` - Price when signal was detected
- `status` - pending, executed, skipped, or failed
- `notes` - Additional information

**Use Case:** Track all signals detected by the scanner, whether executed or not.

### 2. Trades Report

**Columns:**
- `ticker` - Stock symbol
- `timeframe` - Chart timeframe
- `signal_date` - Original signal detection date
- `entry_date` - When position was opened
- `entry_price` - Entry price
- `divergence_type` - Bullish or Bearish
- `direction` - LONG or SHORT
- `initial_shares` - Number of shares initially purchased
- `initial_capital` - Total capital deployed
- `total_pnl` - Total profit/loss in dollars
- `total_pnl_pct` - Total return percentage
- `tp1_status` - Was TP1 (+15%) reached? (Yes/No)
- `tp1_value` - Exit price at TP1 (if reached)
- `tp2_status` - Was TP2 (+18%) reached? (Yes/No)
- `tp2_value` - Exit price at TP2 (if reached)
- `tp3_status` - Was TP3 (+50%) reached? (Yes/No)
- `tp3_value` - Exit price at TP3 (if reached)
- `avg_pnl_per_exit` - Average P&L across all partial exits
- `num_exits` - Number of partial exits (T1, T2, T3, stop)
- `days_in_trade` - How long the position was held
- `exits` - Detailed breakdown of all exits

**Use Case:** Analyze all completed trades with full P&L details and target achievement tracking.

### 3. Analytics Report

**Sections:**

#### Overall Performance
- Total signals, trades, and positions
- Win/loss statistics
- Total P&L and profit factor
- Average win/loss amounts
- Largest win/loss
- Average holding period

#### Yearly P&L (NEW!)
- Year-by-year breakdown
- Trades, wins, losses per year
- Win rate and total P&L by year
- Average P&L per trade by year

#### Quarterly P&L
- Quarter-by-quarter breakdown (YYYY-Q1, YYYY-Q2, etc.)
- Trades, wins, losses per quarter
- Win rate and total P&L by quarter

#### Monthly P&L
- Month-by-month breakdown
- Detailed monthly performance metrics

#### Performance by Timeframe
- Comparison of 1d vs 3d vs 1w signals
- Which timeframe is most profitable

#### Performance by Exit Reason
- Breakdown by T1, T2, T3, stop loss, max hold
- Shows which profit targets are being hit most often

**Use Case:** Comprehensive performance analysis and strategy optimization.

## Opening Reports in Excel/Google Sheets

### Excel
1. Double-click any `.csv` file
2. Data will open automatically in Excel
3. Use "Text to Columns" if needed to separate data

### Google Sheets
1. Go to sheets.google.com
2. File → Import
3. Upload the CSV file
4. Select "Comma" as separator

## Automation

To generate reports automatically on a schedule:

### Daily Reports (7:30 AM ET)
```bash
crontab -e
```

Add this line:
```
30 7 * * * cd ~/trading_bot/rsi_trading_bot && source venv/bin/activate && python reporting.py
```

### Weekly Reports (Sunday 8 PM ET)
```
0 20 * * 0 cd ~/trading_bot/rsi_trading_bot && source venv/bin/activate && python reporting.py
```

## Report Storage

All reports are saved in:
```
~/trading_bot/rsi_trading_bot/reports/
```

### Downloading Reports

**From DigitalOcean Console:**
1. Navigate to the reports directory
2. Use `cat filename.csv` to view
3. Copy and paste into a local file

**Using SCP (if SSH is configured):**
```bash
scp root@174.138.50.219:~/trading_bot/rsi_trading_bot/reports/*.csv ~/Downloads/
```

## Examples

Once the bot starts trading, reports will look like this:

### Example Signals Report
```csv
ticker,timeframe,signal_date,divergence_type,signal_close,status,notes
AAPL,1d,2025-12-10 07:05:32,Bullish,185.50,executed,Detected on 2025-12-10
TSLA,3d,2025-12-10 07:06:15,Bearish,285.20,pending,Detected on 2025-12-10
```

### Example Trades Report
```csv
ticker,timeframe,signal_date,entry_date,entry_price,divergence_type,direction,initial_shares,initial_capital,total_pnl,total_pnl_pct,tp1_status,tp1_value,tp2_status,tp2_value,tp3_status,tp3_value,avg_pnl_per_exit,num_exits,days_in_trade,exits
AAPL,1d,2025-12-10,2025-12-11,186.00,Bullish,LONG,26.8817,5000.00,750.00,15.00,Yes,213.90,No,,No,,750.00,1,12,T1: +15% exit
```

### Example Analytics Yearly P&L
```csv
YEARLY P&L
Year,Trades,Wins,Losses,Win Rate %,Total P&L,Avg P&L
2025,45,32,13,71.11,$12,450.00,$276.67
```

## Tips

1. **Generate reports after significant milestones** (end of week, month, quarter)
2. **Compare analytics over time** to track improvement
3. **Use trades report** to identify which setups work best
4. **Monitor signals report** to ensure scanner is working properly
5. **Archive old reports** to track long-term performance

## Support

If reports are not generating properly:
1. Check that the database file exists: `ls -lh trading_bot.db`
2. Verify Python environment: `source venv/bin/activate`
3. Check for errors: `python reporting.py 2>&1 | tee report_errors.log`
