"""
Show All Trades with Skipped Trades Highlighted

Displays chronological list of all trades showing which were skipped by adaptive filter
"""

import pandas as pd
import os

# Load Scenario A results
script_dir = os.path.dirname(os.path.abspath(__file__))
results_csv = os.path.join(script_dir, 'backtest', 'filter_tests', 'Scenario_A_Skip_After_3_Stops_results.csv')

df = pd.read_csv(results_csv)
df['entry_date'] = pd.to_datetime(df['entry_date'])
df['quarter'] = df['entry_date'].dt.to_period('Q')

print("="*100)
print("ALL TRADES - SCENARIO A: Skip After 3 Consecutive Stop Losses")
print("="*100)
print()

# Summary
total = len(df)
taken = len(df[df['would_take_trade']])
skipped = len(df[~df['would_take_trade']])

print(f"SUMMARY:")
print(f"  Total Trades: {total}")
print(f"  Taken: {taken} ({taken/total*100:.1f}%)")
print(f"  Skipped: {skipped} ({skipped/total*100:.1f}%)")
print()

# Group by quarter
print("BY QUARTER:")
print()
for quarter in sorted(df['quarter'].unique()):
    q_df = df[df['quarter'] == quarter]
    q_taken = len(q_df[q_df['would_take_trade']])
    q_skipped = len(q_df[~q_df['would_take_trade']])
    q_pnl = q_df['total_pnl'].sum()
    q_taken_pnl = q_df[q_df['would_take_trade']]['total_pnl'].sum()
    q_skipped_pnl = q_df[~q_df['would_take_trade']]['total_pnl'].sum()

    print(f"{quarter}:")
    print(f"  Total: {len(q_df)} trades | Taken: {q_taken} | Skipped: {q_skipped}")
    print(f"  Baseline P&L: ${q_pnl:,.2f}")
    print(f"  With Filter: ${q_taken_pnl:,.2f} (Skipped P&L: ${q_skipped_pnl:,.2f})")
    print()

print()
print("="*100)
print("DETAILED TRADE LOG")
print("="*100)
print()

current_quarter = None

for idx, row in df.iterrows():
    # Print quarter header
    if row['quarter'] != current_quarter:
        if current_quarter is not None:
            print()
        print("-"*100)
        print(f"QUARTER: {row['quarter']}")
        print("-"*100)
        current_quarter = row['quarter']

    # Determine status
    status = "✅ TAKEN  " if row['would_take_trade'] else "❌ SKIPPED"

    # Color code P&L
    pnl = row['total_pnl']
    pnl_symbol = "+" if pnl > 0 else ""

    # Build output line
    print(f"{status} | "
          f"{row['entry_date'].strftime('%Y-%m-%d')} | "
          f"{row['ticker']:6s} | "
          f"{row['divergence_type']:8s} | "
          f"Stops: {int(row['consecutive_stops_before'])} | "
          f"P&L: {pnl_symbol}${pnl:7.2f} | "
          f"{row['exit_reasons']}")

print()
print("="*100)
print("LEGEND:")
print("  ✅ TAKEN   = Trade was executed")
print("  ❌ SKIPPED = Trade was blocked by filter")
print("  Stops = Number of consecutive stop losses before this trade (same divergence type)")
print("="*100)
