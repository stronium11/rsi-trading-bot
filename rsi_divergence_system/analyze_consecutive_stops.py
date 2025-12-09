"""
Analyze Maximum Consecutive Stop Losses

Shows the longest consecutive stop loss streaks by quarter and divergence type
"""

import pandas as pd
import os


def analyze_consecutive_stops():
    """Analyze max consecutive stop losses in the data"""
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Load optimized results
    results_csv = os.path.join(script_dir, 'backtest', 'optimized_results', 'trades_summary.csv')
    df = pd.read_csv(results_csv)

    # Parse dates
    df['entry_date'] = pd.to_datetime(df['entry_date'])
    df['quarter'] = df['entry_date'].dt.to_period('Q')

    # Sort chronologically
    df = df.sort_values('entry_date').reset_index(drop=True)

    def is_stop_loss(row):
        """Check if trade was a LOSING stop loss"""
        has_stop_loss = 'Stop Loss' in str(row['exit_reasons'])
        is_loser = row['total_pnl'] <= 0
        return has_stop_loss and is_loser

    # Track consecutive stops
    max_streaks = []

    for quarter in df['quarter'].unique():
        quarter_df = df[df['quarter'] == quarter]

        for div_type in ['Bullish', 'Bearish']:
            type_df = quarter_df[quarter_df['divergence_type'] == div_type]

            if len(type_df) == 0:
                continue

            # Track consecutive stops
            current_streak = 0
            max_streak = 0

            for idx, row in type_df.iterrows():
                if is_stop_loss(row):
                    current_streak += 1
                    max_streak = max(max_streak, current_streak)
                else:
                    current_streak = 0

            if max_streak > 0:
                max_streaks.append({
                    'quarter': str(quarter),
                    'divergence_type': div_type,
                    'max_consecutive_stops': max_streak,
                    'total_trades': len(type_df)
                })

    # Convert to DataFrame and sort
    streaks_df = pd.DataFrame(max_streaks)
    streaks_df = streaks_df.sort_values('max_consecutive_stops', ascending=False)

    print("="*70)
    print("MAXIMUM CONSECUTIVE STOP LOSSES BY QUARTER")
    print("="*70)
    print()

    # Overall max
    overall_max = streaks_df['max_consecutive_stops'].max()
    print(f"HIGHEST CONSECUTIVE STOPS EVER: {overall_max}")
    print()

    # Top 20 quarters
    print("TOP 20 WORST STREAKS:")
    print("-"*70)
    print(streaks_df.head(20).to_string(index=False))
    print()

    # Summary by threshold
    print("THRESHOLD ANALYSIS:")
    print("-"*70)
    for threshold in [3, 6, 10, 15, 20]:
        would_trigger = len(streaks_df[streaks_df['max_consecutive_stops'] >= threshold])
        print(f"  {threshold} consecutive stops: Would trigger in {would_trigger} quarter/type combinations")

    print()
    print("="*70)


if __name__ == "__main__":
    analyze_consecutive_stops()
