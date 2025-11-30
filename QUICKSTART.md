# Quick Start Guide - SMA Trading Signal System

## From Scratch Setup (Any Computer)

If you need to set up this system on a new computer or after losing local files:

### 1. Clone the Repository

```bash
# Navigate to where you want the project
cd ~

# Clone from GitHub
git clone https://github.com/stronium11/stronium11.git

# Enter the directory
cd stronium11

# Switch to the working branch
git checkout claude/new-session-01KGn64EGQ67EAgEAdcd5fiM
```

### 2. Install Dependencies

```bash
# Install required Python packages
pip3 install -r requirements.txt
```

**Note:** If you get errors installing, you may need to install packages individually:
```bash
pip3 install pandas numpy yfinance
```

### 3. Run the System

```bash
# Full scan of all NASDAQ 100 stocks
python3 main.py

# Test with a few stocks
python3 main.py --test

# Scan specific tickers
python3 main.py --tickers AAPL MSFT NVDA

# Scan for a historical date
python3 main.py --date 2025-11-25

# Debug mode (see why signals are filtered)
python3 main.py --debug

# View summary of all logged signals
python3 main.py --summary
```

---

## Daily Usage

### Morning Routine

```bash
cd ~/stronium11
python3 main.py
```

This will:
- Scan all 96 NASDAQ 100 stocks
- Check for price touches on SMAs (50, 100, 200)
- Validate trends (bullish/bearish)
- Filter out duplicates
- Save new signals to `trading_signals.csv`

### View Your Signals

```bash
# Open in Excel/Numbers
open trading_signals.csv

# Or view in terminal
cat trading_signals.csv
```

### Import to Google Sheets

1. Open your Google Sheet
2. File → Import → Upload
3. Select `trading_signals.csv`
4. Choose "Append to current sheet"

---

## File Structure

```
stronium11/
├── main.py                  # Entry point - run this
├── scanner.py              # Main scanning logic
├── data_fetcher.py         # Fetches stock data from Yahoo Finance
├── sma_calculator.py       # SMA calculations
├── trend_validator.py      # Trend validation logic
├── signal_detector.py      # Signal detection
├── deduplicator.py         # Prevents duplicate signals
├── logger.py               # Logs signals to CSV
├── config.py               # Configuration (thresholds, periods)
├── demo_data.py            # Demo data generator
├── demo.py                 # Demo mode runner
├── requirements.txt        # Python dependencies
├── README_TRADING.md       # System overview
├── SIGNAL_CRITERIA.md      # Signal qualification criteria
└── trading_signals.csv     # Your signals (generated)
```

---

## Output Files

**trading_signals.csv** - All detected signals (CSV format)
- Date, Asset Name, SMA Affected, Timeframe, Trend, Price, etc.
- Import this to Google Sheets
- **Backed up:** No (regenerated each run)

**signals_history.json** - Deduplication tracker
- Stores which signals have been registered
- Prevents duplicate alerts
- **Backed up:** No (delete to reset)

---

## Troubleshooting

### "No signals logged yet"

This is normal! It means:
- No stocks are currently touching their SMAs, OR
- All detected signals are duplicates (already registered)

Try historical scans to see signals from past dates:
```bash
python3 main.py --date 2025-11-25
```

### "Module not found" errors

Reinstall dependencies:
```bash
pip3 install -r requirements.txt
```

### Signals changing between runs

The deduplicator filters out signals already seen. Delete history to reset:
```bash
rm signals_history.json
python3 main.py
```

### Yahoo Finance errors (403, 404)

Yahoo Finance sometimes rate-limits or blocks requests. Wait a few minutes and try again.

---

## Updating the System

If the code is updated on GitHub:

```bash
cd ~/stronium11
git pull
```

---

## Backup Your Signals

```bash
# Copy signals to Desktop with date
cp trading_signals.csv ~/Desktop/signals_$(date +%Y%m%d).csv

# Or backup to iCloud/Dropbox
cp trading_signals.csv ~/Library/Mobile\ Documents/com~apple~CloudDocs/
```

---

## Advanced Usage

### Change Thresholds

Edit `config.py` to adjust:
- SMA periods (default: 50, 100, 200)
- Timeframes (default: 1d, 3d, 1w)
- Proximity threshold (default: 0.5%)
- Separation threshold (default: 0.5%)

### Debug Mode

See why stocks are/aren't generating signals:
```bash
python3 main.py --tickers AAPL NVDA TSLA --debug
```

### Demo Mode

Test the system with generated data:
```bash
DEMO_MODE=true python3 main.py --test
```

---

## Support

- **Documentation:** See `SIGNAL_CRITERIA.md` for signal logic
- **Code:** All files are commented
- **GitHub:** https://github.com/stronium11/stronium11

---

## Recovery Checklist

If you lose everything, you need:
1. ✅ GitHub account access (to clone the repo)
2. ✅ Python 3 installed on your Mac
3. ✅ Internet connection (to fetch stock data)
4. ✅ This guide!

**Time to recover:** ~5 minutes
