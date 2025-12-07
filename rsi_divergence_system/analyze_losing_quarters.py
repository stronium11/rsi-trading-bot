"""
Analyze Losing Quarters

Extracts detailed trade data for quarters with negative P&L
"""

import pandas as pd
import os

# Define losing quarters
losing_quarters = ['2022Q3', '2022Q4', '2023Q1', '2023Q2', '2024Q2', '2025Q3']

# Load trades summary
script_dir = os.path.dirname(os.path.abspath(__file__))
summary_csv = os.path.join(script_dir, 'backtest', 'optimized_results', 'trades_summary.csv')
df = pd.read_csv(summary_csv)

# Parse dates and create quarter column
df['entry_date'] = pd.to_datetime(df['entry_date'])
df['final_exit_date'] = pd.to_datetime(df['final_exit_date'])
df['quarter'] = df['entry_date'].dt.to_period('Q').astype(str)

# Filter for losing quarters
losing_df = df[df['quarter'].isin(losing_quarters)]

# Sort by quarter and entry date
losing_df = losing_df.sort_values(['quarter', 'entry_date'])

# Export detailed losing trades
output_csv = os.path.join(script_dir, 'backtest', 'optimized_results', 'losing_quarters_analysis.csv')
losing_df.to_csv(output_csv, index=False)

print("="*70)
print("LOSING QUARTERS ANALYSIS")
print("="*70)
print()

# Analyze each quarter
for quarter in losing_quarters:
    q_df = losing_df[losing_df['quarter'] == quarter]

    if len(q_df) == 0:
        continue

    winners = len(q_df[q_df['total_pnl'] > 0])
    losers = len(q_df[q_df['total_pnl'] <= 0])
    total_pnl = q_df['total_pnl'].sum()

    print(f"{quarter}")
    print("-"*70)
    print(f"  Total Trades: {len(q_df)}")
    print(f"  Winners: {winners} | Losers: {losers}")
    print(f"  Total P&L: ${total_pnl:,.2f}")
    print()

    # Show each trade
    for idx, row in q_df.iterrows():
        win_loss = "✅ WIN" if row['total_pnl'] > 0 else "❌ LOSS"
        print(f"  {row['ticker']} | {row['timeframe']} | {row['divergence_type']} | "
              f"Entry: {row['entry_date'].strftime('%Y-%m-%d')} @ ${row['entry_price']:.2f} | "
              f"Exit: {row['final_exit_date'].strftime('%Y-%m-%d')} | "
              f"Days: {row['days_held']} | "
              f"P&L: ${row['total_pnl']:.2f} {win_loss} | "
              f"Exits: {row['exit_reasons']}")
    print()
    print()

print("="*70)
print(f"Detailed data exported to: {output_csv}")
print("="*70)

# Summary statistics
print()
print("SUMMARY STATISTICS")
print("-"*70)
print()

# By timeframe
print("By Timeframe:")
for tf in losing_df['timeframe'].unique():
    tf_df = losing_df[losing_df['timeframe'] == tf]
    print(f"  {tf}: {len(tf_df)} trades, ${tf_df['total_pnl'].sum():.2f} total P&L")
print()

# By type
print("By Type:")
for div_type in losing_df['divergence_type'].unique():
    type_df = losing_df[losing_df['divergence_type'] == div_type]
    print(f"  {div_type}: {len(type_df)} trades, ${type_df['total_pnl'].sum():.2f} total P&L")
print()

# By exit reason
print("Most Common Exit Reasons:")
exit_reasons_list = []
for reasons in losing_df['exit_reasons']:
    exit_reasons_list.extend(reasons.split(', '))
exit_reasons_series = pd.Series(exit_reasons_list)
print(exit_reasons_series.value_counts().head(10))
print()

# Worst performers
print("Top 10 Worst Trades:")
worst_trades = losing_df.nsmallest(10, 'total_pnl')[['ticker', 'timeframe', 'divergence_type', 'entry_date', 'total_pnl']]
for idx, row in worst_trades.iterrows():
    print(f"  {row['ticker']} | {row['timeframe']} | {row['divergence_type']} | "
          f"{pd.to_datetime(row['entry_date']).strftime('%Y-%m-%d')} | ${row['total_pnl']:.2f}")
