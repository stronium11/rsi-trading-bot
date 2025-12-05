# Critical Bug Fixes in Trade Simulator

## Date: 2025-12-05

## Summary
The original `TradeSimulator` in `advanced_rule_optimizer.py` contained critical bugs that invalidated all optimization results. This document explains the bugs, fixes, and what needs to be re-run.

---

## Bugs Found

### BUG #1: Multiple Exits on Same Day ⚠️ **CRITICAL**

**Problem:**
- T1 and T2 (and T3) could all fire on the same trading day
- When T1=T2 (e.g., both at +15%), BOTH would execute on the same bar
- This made T2=T1 appear optimal, when it was really just closing 100% at +15%

**Original Code (Lines 175-195):**
```python
# Target 1
if profit_pct >= target1_pct and len(self.exits) == 0:
    self.execute_exit(...)  # Fires, now len(exits) == 1

# Target 2 - CHECKS IMMEDIATELY AFTER!
if profit_pct >= target2_pct and len(self.exits) == 1:
    self.execute_exit(...)  # Fires same day if T2=T1!
```

**Fix:**
```python
# Added tracking of last_exit_date
self.last_exit_date = None

# Skip target checks if already exited today
if self.last_exit_date is not None and self.last_exit_date.date() == date.date():
    continue  # Skip all target checks

# After each exit
self.last_exit_date = date  # Track when we exited
continue  # Skip remaining target checks this day
```

**Impact:** This bug made Phase 2 & 3 optimization results completely invalid.

---

### BUG #2: No Target Level Validation

**Problem:**
- No check to ensure T2 > T1 and T3 > T2
- Allowed illogical configurations like T2=T1 or T3 < T2

**Fix:**
```python
def _validate_rules(self):
    """Validate that rules make logical sense"""
    t1 = self.rules.get('target1_pct', 10)
    t2 = self.rules.get('target2_pct', 20)
    t3 = self.rules.get('target3_pct', 50)

    if t2 <= t1:
        raise ValueError(f"Target 2 ({t2}%) must be greater than Target 1 ({t1}%)")
    if t3 <= t2:
        raise ValueError(f"Target 3 ({t3}%) must be greater than Target 2 ({t2}%)")
```

**Impact:** Now impossible to test invalid configurations.

---

### BUG #3: Position Sizing Validation

**Problem:**
- No check that T1_size + T2_size <= 100%
- Could accidentally try to close 110% of position

**Fix:**
```python
total_size = t1_size + t2_size
if total_size > 100:
    raise ValueError(f"T1 size ({t1_size}%) + T2 size ({t2_size}%) = {total_size}% exceeds 100%")
```

**Impact:** Prevents configuration errors.

---

## What This Means

### ❌ INVALID Results (Must Re-Run):

1. **Phase 2 Optimization (Target 1)**
   - Result showed T1 +15% (70%) as optimal
   - **May be affected** by same-day exit bug
   - Need to re-test

2. **Phase 3 Optimization (Target 2)**
   - Result showed T2 +15% (30%) as optimal (same as T1!)
   - **COMPLETELY INVALID** due to Bug #1
   - This was an artifact of the bug

3. **Phase 4 Optimization (Trailing/T3)**
   - Built on flawed Phase 3 results
   - **INVALID** and needs re-run

### ✅ PROBABLY VALID Results:

1. **Phase 1 Optimization (Stop Loss)**
   - Result: -7% stop is optimal
   - **Likely still valid** - stop loss logic was separate from target logic
   - Showed clear peak at -7%, declining at -8%
   - Should still re-test to be certain

---

## Action Required

### Step 1: Re-Run Iterative Optimizer

The corrected `iterative_optimizer.py` now uses `CorrectedTradeSimulator`:

```bash
cd /path/to/stronium11/rsi_divergence_system

# Pull latest fixes
git pull origin claude/rsi-signal-system-016Ch1qMCkuLd6m8X8ZRb9ap

# Re-run optimization (price data already cached!)
python3 iterative_optimizer.py
```

**Expected Runtime:** ~10 minutes (cache already exists, so no 8-min fetch time)

### Step 2: Compare Results

Compare new results to original:

**Original (Buggy):**
- Stop: -7%
- T1: +15% (70%)
- T2: +15% (30%) ← Bug artifact
- T3: +30%
- Total P&L: $11,885
- Improvement: +22.4%

**New (Corrected):**
- Stop: TBD
- T1: TBD
- T2: TBD (must be > T1!)
- T3: TBD
- Total P&L: TBD
- Improvement: TBD

---

## Files Changed

1. **NEW:** `corrected_trade_simulator.py`
   - Fixed version with all bugs addressed
   - Includes comprehensive validators
   - Prevents same-day multi-exits

2. **UPDATED:** `iterative_optimizer.py`
   - Now imports and uses `CorrectedTradeSimulator`
   - Line 15: Import changed
   - Line 203: Instantiation changed

3. **UNCHANGED:** `advanced_rule_optimizer.py`
   - Original buggy version kept for reference
   - DO NOT USE for new optimizations

---

## Testing

All validators tested and passing:

```bash
python3 corrected_trade_simulator.py

✅ Test 1 PASSED: Valid rules accepted
✅ Test 2 PASSED: Correctly rejected T2=T1
✅ Test 3 PASSED: Correctly rejected T2<T1
✅ Test 4 PASSED: Correctly rejected T3=T2
✅ Test 5 PASSED: Correctly rejected oversizing
```

---

## Next Steps

1. ✅ **DONE:** Fixed TradeSimulator bugs
2. ✅ **DONE:** Updated iterative_optimizer.py
3. ⏳ **TODO:** Re-run optimization on your Mac
4. ⏳ **TODO:** Compare corrected results to original
5. ⏳ **TODO:** Implement validated optimal rules
6. ⏳ **TODO:** Re-run full backtest with correct rules

---

## Questions?

If corrected optimization shows T2 > T1 but lower total P&L, it suggests:
- The original "T2=T1" result was indeed a bug artifact
- The bug accidentally found a strategy (close 100% at +15%)
- We should explicitly test single-exit strategies

Good luck with the corrected run! 🚀
