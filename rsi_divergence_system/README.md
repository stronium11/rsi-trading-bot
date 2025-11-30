# RSI Divergence Detection System

A standalone automated trading signal system that scans Nasdaq 100 stocks for RSI (Relative Strength Index) divergences across multiple timeframes.

## Overview

This system detects bullish and bearish divergences between price action and RSI indicator, which are potential trading signals that indicate trend reversals.

### What are RSI Divergences?

- **Bearish Divergence**: Occurs when price makes higher highs (HH) but RSI makes lower highs (LH) - indicates potential downward reversal
- **Bullish Divergence**: Occurs when price makes lower lows (LL) but RSI makes higher lows (HL) - indicates potential upward reversal

## Features

- Scans all 100 Nasdaq 100 stocks
- Multiple timeframe analysis: 1h, 4h, 1d, 3d
- Automatic signal logging to CSV file
- Configurable RSI parameters
- Rate-limited API calls to respect data provider limits
- Standalone operation (completely separate from other trading systems)

## Installation

1. Navigate to the system directory:
```bash
cd rsi_divergence_system
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Scan All Nasdaq 100 Stocks

Scan all tickers across all timeframes (1h, 4h, 1d, 3d):
```bash
python main.py
```

### Scan a Specific Ticker

Scan a single stock symbol:
```bash
python main.py --ticker AAPL
```

### Scan Specific Timeframes

Scan only certain timeframes:
```bash
python main.py --timeframes 1h 1d
```

### Combine Ticker and Timeframe Options

```bash
python main.py --ticker TSLA --timeframes 1h 4h
```

### View Recent Signals

View the 20 most recent signals detected:
```bash
python main.py --view-signals 20
```

### Custom CSV Output Path

Specify a custom path for the signal log file:
```bash
python main.py --csv-path data/my_signals.csv
```

## Output Format

Signals are logged to `logs/rsi_divergence_signals.csv` with the following columns:

| Column | Description |
|--------|-------------|
| `detection_date` | Date when the divergence was detected (date of 2nd peak) |
| `ticker` | Stock ticker symbol |
| `timeframe` | Timeframe where divergence was detected (1h, 4h, 1d, 3d) |
| `divergence_type` | Type of divergence (Bearish or Bullish) |
| `first_peak_price` | Actual price at the 1st price action peak |
| `second_peak_price` | Actual price at the 2nd price action peak |
| `first_peak_rsi` | RSI value at the 1st price action peak |
| `second_peak_rsi` | RSI value at the 2nd price action peak |

## Project Structure

```
rsi_divergence_system/
├── main.py                      # Main entry point
├── rsi_divergence_detector.py   # RSI divergence detection logic
├── market_scanner.py            # Market scanning functionality
├── signal_logger.py             # CSV logging system
├── nasdaq100_tickers.py         # List of Nasdaq 100 tickers
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── data/                        # Data storage (optional)
└── logs/                        # Signal logs directory
    └── rsi_divergence_signals.csv
```

## How It Works

1. **Data Fetching**: Downloads historical price data from Yahoo Finance for each ticker
2. **RSI Calculation**: Computes RSI indicator (default 14-period) for the price data
3. **Peak Detection**: Identifies local maxima and minima in both price and RSI
4. **Divergence Detection**: Compares peaks to find divergence patterns:
   - Bearish: Price higher high + RSI lower high
   - Bullish: Price lower low + RSI higher low
5. **Signal Logging**: Records detected divergences to CSV file with all relevant details

## Configuration

You can modify detection parameters in the code:

- **RSI Period**: Default is 14 (in `rsi_divergence_detector.py`)
- **Peak Detection Order**: Default is 5 (controls sensitivity)
- **Lookback Period**: Default is 20 bars (maximum distance between peaks)

## Important Notes

- This system is completely standalone and separate from any SMA-based systems
- API rate limiting is implemented (0.5s delay between requests) to avoid overwhelming data providers
- Full scans of all Nasdaq 100 stocks may take several minutes
- Hourly data (1h, 4h) is limited to approximately 60 days of history by Yahoo Finance
- The system removes duplicate signals automatically

## Example Workflow

1. Run a full market scan:
```bash
python main.py
```

2. Review the signals:
```bash
python main.py --view-signals 50
```

3. Investigate specific interesting tickers:
```bash
python main.py --ticker NVDA
```

4. Focus on daily timeframes for longer-term signals:
```bash
python main.py --timeframes 1d 3d
```

## Dependencies

- `pandas` - Data manipulation and analysis
- `numpy` - Numerical computing
- `yfinance` - Yahoo Finance data downloader
- `ta` - Technical analysis library (RSI calculation)
- `scipy` - Peak detection algorithms

## Troubleshooting

**Issue**: No data returned for a ticker
- Some tickers may have limited historical data for certain timeframes
- Try different timeframes or check if the ticker symbol is correct

**Issue**: Rate limit errors
- The system includes built-in delays, but you can increase the `time.sleep()` value in `market_scanner.py`

**Issue**: Import errors
- Ensure all dependencies are installed: `pip install -r requirements.txt`

## Future Enhancements

Potential improvements for future versions:
- Email/SMS notifications for new signals
- Web dashboard for signal visualization
- Backtesting functionality
- Integration with other technical indicators
- Real-time scanning (currently historical data only)

## License

This is a standalone trading signal detection system for educational and research purposes.

## Disclaimer

This system is for informational purposes only. Trading signals should not be used as the sole basis for investment decisions. Always conduct your own research and consider consulting with a financial advisor.
