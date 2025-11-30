# RSI Divergence Detection System

## Standalone system for detecting RSI divergences in NASDAQ 100 stocks

This is a **separate system** from the SMA trading signal detector. It identifies bullish and bearish RSI divergences.

## What It Does

Detects **divergences** between price action and RSI indicator:

- **Bearish Divergence**: Price makes higher high, RSI makes lower high → Potential reversal down
- **Bullish Divergence**: Price makes lower low, RSI makes higher low → Potential reversal up

## Installation

```bash
cd rsi_divergence_system
pip3 install -r requirements.txt
```

## Usage

```bash
# Scan all NASDAQ 100
python3 main.py

# Test with a few stocks
python3 main.py --test

# Scan specific tickers
python3 main.py --tickers AAPL MSFT NVDA

# View summary
python3 main.py --summary
```

## Output

Signals are logged to `rsi_divergence_signals.csv` with:
- Date (of 2nd peak)
- Ticker
- Timeframe
- Divergence Type (Bullish/Bearish)
- First Peak Price
- Second Peak Price
- First Peak RSI
- Second Peak RSI
- Bars Between Peaks

## Timeframes

- 1h (hourly)
- 4h (4-hour)
- 1d (daily)
- 3d (3-day)

## Parameters

Edit `config.py` to adjust:
- RSI period (default: 14)
- Divergence lookback (default: 20 bars)
- Sensitivity (order: 5)
