# RSI Divergence Detection System

Standalone system for detecting RSI divergences in NASDAQ 100 stocks.

## Installation

```bash
cd rsi_divergence_system
pip3 install -r requirements.txt
```

## Usage

```bash
# Test scan
python3 main.py --test

# Scan specific tickers
python3 main.py --tickers AAPL MSFT NVDA

# Full NASDAQ 100 scan
python3 main.py

# View summary
python3 main.py --summary
```

## Output

Signals saved to: `rsi_divergence_signals.csv`

Columns:
- Date (2nd peak)
- Ticker
- Timeframe
- Divergence Type (Bullish/Bearish)
- First Peak Price
- Second Peak Price
- First Peak RSI
- Second Peak RSI

## Timeframes

1h, 4h, 1d, 3d
