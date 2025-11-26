# SMA Trading Signal System

A trend-following trading signal system that monitors NASDAQ 100 stocks for SMA (Simple Moving Average) crossovers and price touches.

## Features

- **Multi-timeframe Analysis**: Monitors 1D, 3D, and 1W timeframes
- **SMA Periods**: Tracks 50, 100, and 200-period SMAs
- **Trend Detection**: Identifies clear bullish and bearish trends with:
  - Minimum 0.5% SMA separation requirement
  - Trend stability validation over historical periods
- **Signal Detection**: Alerts when price comes within 0.5% of any SMA
- **Deduplication**: Prevents duplicate signals for consecutive days
- **CSV Logging**: Exports signals to CSV for easy import to Google Sheets

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Usage

### Run Full Scan (All NASDAQ 100)
```bash
python main.py
```

### Test with Sample Stocks
```bash
python main.py --test
```

### Scan Specific Tickers
```bash
python main.py --tickers AAPL MSFT NVDA
```

### View Signal Summary
```bash
python main.py --summary
```

## Configuration

Edit `config.py` to customize:
- SMA periods
- Timeframes
- Proximity thresholds
- Separation requirements
- Output file paths

## Signal Requirements

A signal is generated when ALL conditions are met:

1. **Trend Validation**:
   - SMA 50 must be ≥0.5% above/below SMA 100
   - SMA 100 must be ≥0.5% above/below SMA 200
   - Same alignment must have existed N days ago (stability check)

2. **Price Proximity**:
   - Current price within 0.5% of any SMA (50, 100, or 200)

3. **Not a Duplicate**:
   - Same signal type not registered in previous trading day

## Output

Signals are logged to `trading_signals.csv` with columns:
- Date
- Asset Name
- SMA Affected (50/100/200)
- Timeframe (1d/3d/1w)
- Trend (bullish/bearish)
- Signal Price
- SMA Value
- Distance %
- Timestamp

## Importing to Google Sheets

1. Run the scanner: `python main.py`
2. Open your Google Sheet
3. File → Import → Upload → Select `trading_signals.csv`
4. Choose "Append to current sheet"

## System Architecture

```
main.py              # Entry point
├── scanner.py       # Orchestrates scanning
├── data_fetcher.py  # Fetches market data (yfinance)
├── sma_calculator.py # Calculates SMAs
├── trend_validator.py # Validates trends
├── signal_detector.py # Detects signals
├── deduplicator.py  # Prevents duplicates
└── logger.py        # Logs to CSV
```

## Requirements

- Python 3.8+
- yfinance (market data)
- pandas (data manipulation)
- numpy (calculations)

## Notes

- Data is fetched from Yahoo Finance (free, no API key required)
- Historical data period: 1 year (configurable)
- Signal history stored in `signals_history.json`
- Supports both bullish and bearish trend following
