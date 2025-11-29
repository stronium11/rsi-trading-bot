# Signal Qualification Criteria

This document explains all the factors and filters used to determine if a valid trading signal should be registered.

## Overview

The system generates signals when a stock's price touches or approaches a Simple Moving Average (SMA) during a confirmed trend. Multiple strict criteria must be met for a signal to be registered.

---

## Signal Generation Process

```
Stock Data → SMA Calculation → Trend Validation → Signal Detection → Deduplication → Logged Signal
```

---

## 1. SMA Calculation

**What it does:** Calculates Simple Moving Averages for each stock.

**Parameters:**
- **SMA Periods:** 50, 100, and 200 days
- **Timeframes:** 1D (daily), 3D (3-day), 1W (weekly)

**Requirement:**
- Sufficient historical data must exist to calculate all three SMAs
- Minimum ~200 trading days of data required

---

## 2. Trend Validation

A valid trend must pass **TWO checks**: SMA Separation AND Trend Stability.

### 2.1 SMA Separation Check

**Purpose:** Ensure SMAs are properly aligned and separated to confirm a clear trend.

**Bullish Trend Requirements:**
- SMA 50 ≥ SMA 100 × 1.005 (SMA 50 is at least 0.5% above SMA 100)
- **AND** SMA 100 ≥ SMA 200 × 1.005 (SMA 100 is at least 0.5% above SMA 200)

**Bearish Trend Requirements:**
- SMA 50 ≤ SMA 100 × 0.995 (SMA 50 is at least 0.5% below SMA 100)
- **AND** SMA 100 ≤ SMA 200 × 0.995 (SMA 100 is at least 0.5% below SMA 200)

**Why 0.5%?**
This minimum separation prevents false signals during choppy/sideways markets where SMAs are tangled together.

**Example - Bullish Trend:**
```
SMA 50:  $155.00
SMA 100: $154.00 (must be ≤ $154.23 for 0.5% separation)
SMA 200: $150.00 (must be ≤ $153.23 for 0.5% separation)
✓ Valid bullish trend
```

**Example - No Clear Trend:**
```
SMA 50:  $155.00
SMA 100: $154.90 (only 0.06% apart - too close!)
SMA 200: $154.80
✗ No valid trend - SMAs too mixed
```

### 2.2 Trend Stability Check

**Purpose:** Confirm the trend has been stable over time, not a recent fluke.

**Requirements:**
- The same SMA alignment must have existed N trading days ago
- **1D timeframe:** Must have been aligned 14 trading days ago
- **3D timeframe:** Must have been aligned 25 trading days ago
- **1W timeframe:** Must have been aligned 25 trading days ago

**Why stability matters:**
Prevents signals during trend transitions when SMAs are just crossing over.

**Example - Stable Bullish Trend:**
```
Today:      SMA 50 > SMA 100 > SMA 200 (properly separated)
14 days ago: SMA 50 > SMA 100 > SMA 200 (properly separated)
✓ Stable trend confirmed
```

**Example - Unstable Trend:**
```
Today:      SMA 50 > SMA 100 > SMA 200 (bullish)
14 days ago: SMA 50 < SMA 100 < SMA 200 (bearish)
✗ Trend not stable - recently changed direction
```

---

## 3. Price Proximity Detection

**What it checks:** Is the current price close enough to an SMA to constitute a "touch"?

**Requirement:**
- Price must be within **0.5%** of any SMA (50, 100, or 200)

**Calculation:**
```
Lower Bound = SMA × 0.995 (SMA minus 0.5%)
Upper Bound = SMA × 1.005 (SMA plus 0.5%)

If Lower Bound ≤ Current Price ≤ Upper Bound → Signal detected
```

**Example:**
```
SMA 100: $150.00
Lower Bound: $149.25 ($150.00 × 0.995)
Upper Bound: $150.75 ($150.00 × 1.005)

Current Price: $150.50 ✓ Within range - Signal detected!
Current Price: $151.00 ✗ Too far (0.67% away) - No signal
```

---

## 4. Deduplication Filter

**Purpose:** Prevent duplicate notifications when a stock continues touching the same SMA on consecutive days.

**How it works:**
- System stores the date of each signal in `signals_history.json`
- Before registering a new signal, checks if the same signal (ticker + SMA + timeframe) was already registered recently
- For **1D timeframe:** Skips signal if registered within last 1 day
- For **3D/1W timeframes:** Skips signal if registered within last 3 days

**Example:**
```
Monday:    AAPL touches SMA 50 on 1D → Signal registered ✓
Tuesday:   AAPL still touching SMA 50 on 1D → Duplicate, skipped ✗
Wednesday: AAPL bounces away then returns to SMA 50 → New signal ✓
```

---

## Complete Signal Qualification Checklist

For a signal to be registered, **ALL** of the following must be true:

- [ ] Stock has sufficient historical data (200+ trading days)
- [ ] **SMA Separation:** SMAs are separated by at least 0.5%
- [ ] **Trend Alignment:** SMAs are in bullish OR bearish order
- [ ] **Trend Stability:** Same alignment existed N days ago (14-25 days depending on timeframe)
- [ ] **Price Proximity:** Current price is within 0.5% of at least one SMA (50, 100, or 200)
- [ ] **Not a Duplicate:** Same signal was not registered in the last 1-3 days

If **ANY** criterion fails → **No signal is registered**

---

## Signal Output

When all criteria are met, the system logs:

| Field | Description | Example |
|-------|-------------|---------|
| Date | Trading date of the signal | 2025-11-26 |
| Asset Name | Stock ticker | NVDA |
| SMA Affected | Which SMA was touched | 100 |
| Timeframe | Chart timeframe | 1d |
| Trend | Direction of trend | bullish |
| Signal Price | Price at signal time | $156.26 |
| SMA Value | Exact SMA value | $155.34 |
| Distance % | How close to SMA | 0.59% |
| Timestamp | When signal was logged | 2025-11-26 14:30:15 |

---

## Why These Criteria?

**Quality over Quantity:** These strict filters ensure you only receive high-probability signals during confirmed trends, not noise from choppy markets.

**Trend Following:** The system is designed for trend-following strategies where price pullbacks to SMAs serve as entry points.

**No False Alarms:** The stability check and deduplication prevent premature signals during trend changes or when price is just riding an SMA.

---

## Typical Signal Scenarios

### ✓ Valid Bullish Signal
```
Context: Strong uptrend for weeks
Scenario: Price pulls back to SMA 50 after a rally
SMAs: 50 ($155) > 100 ($150) > 200 ($145) - well separated
Stability: Same alignment 14 days ago
Price: $155.20 (within 0.5% of SMA 50)
Result: SIGNAL REGISTERED → Potential buy opportunity
```

### ✗ Invalid - No Clear Trend
```
Context: Sideways/choppy market
SMAs: 50 ($150) ≈ 100 ($149.80) ≈ 200 ($149.50) - too close
Result: NO SIGNAL → SMAs not separated enough
```

### ✗ Invalid - Trend Just Started
```
Context: SMAs just crossed over yesterday
Today: 50 ($155) > 100 ($150) > 200 ($145)
14 days ago: 50 ($148) < 100 ($150) < 200 ($152)
Result: NO SIGNAL → Trend not stable yet
```

### ✗ Invalid - Price Too Far
```
Context: Clear uptrend but price not at SMA
SMAs: Perfect bullish alignment
Price: $160 (SMA 50 is at $155)
Distance: 3.2% away
Result: NO SIGNAL → Price not close enough to any SMA
```

### ✗ Invalid - Duplicate
```
Yesterday: Signal registered for AAPL touching SMA 50
Today: AAPL still touching SMA 50
Result: NO SIGNAL → Duplicate filtered out
```

---

## Configuration

All thresholds can be adjusted in `config.py`:

```python
# Proximity threshold - how close price must be to SMA
PRICE_PROXIMITY_THRESHOLD = 0.005  # 0.5%

# Separation threshold - minimum gap between SMAs
SMA_SEPARATION_THRESHOLD = 0.005   # 0.5%

# Stability check periods by timeframe
TIMEFRAMES = {
    '1d': {'stability_check_days': 14},
    '3d': {'stability_check_days': 25},
    '1w': {'stability_check_days': 25}
}
```

---

## Summary

The system uses a **multi-layer validation approach** to ensure only high-quality signals are generated:

1. **Technical Analysis:** SMAs properly aligned and separated
2. **Time Validation:** Trend confirmed over historical period
3. **Price Action:** Actual touch/approach to SMA level
4. **Smart Filtering:** No duplicates or noise

This results in fewer but much higher-quality trading signals.
