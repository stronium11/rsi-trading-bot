"""
Export Trade Status Report

Creates a clean CSV with all trades showing status (TAKEN/SKIPPED) for easy analysis.
"""

import pandas as pd
import os


def export_trade_status():
    """Export all trades with status column"""
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Load Scenario A results
    results_csv = os.path.join(script_dir, 'backtest', 'filter_tests',
                               'Scenario_A_Skip_After_3_Stops_results.csv')

    df = pd.read_csv(results_csv)

    # Create clean export with key columns
    export_df = pd.DataFrame({
        'entry_date': pd.to_datetime(df['entry_date']).dt.strftime('%Y-%m-%d'),
        'ticker': df['ticker'],
        'timeframe': df['timeframe'],
        'divergence_type': df['divergence_type'],
        'status': df['would_take_trade'].apply(lambda x: 'TAKEN' if x else 'SKIPPED'),
        'consecutive_stops_before': df['consecutive_stops_before'].astype(int),
        'total_pnl': df['total_pnl'].round(2),
        'entry_price': df['entry_price'].round(2),
        'exit_reasons': df['exit_reasons'],
        'quarter': df['quarter']
    })

    # Sort chronologically
    export_df = export_df.sort_values('entry_date').reset_index(drop=True)

    # Export to CSV
    output_csv = os.path.join(script_dir, 'backtest', 'filter_tests',
                              'all_trades_with_status.csv')
    export_df.to_csv(output_csv, index=False)

    print("="*70)
    print("ALL TRADES WITH STATUS")
    print("="*70)
    print()
    print(f"Total Trades: {len(export_df)}")
    print(f"  Taken: {len(export_df[export_df['status'] == 'TAKEN'])}")
    print(f"  Skipped: {len(export_df[export_df['status'] == 'SKIPPED'])}")
    print()

    # Show summary by status
    print("SUMMARY BY STATUS:")
    print("-"*70)
    for status in ['TAKEN', 'SKIPPED']:
        subset = export_df[export_df['status'] == status]
        winners = len(subset[subset['total_pnl'] > 0])
        total_pnl = subset['total_pnl'].sum()

        print(f"\n{status}:")
        print(f"  Trades: {len(subset)}")
        print(f"  Winners: {winners} ({100*winners/len(subset):.1f}%)")
        print(f"  Total P&L: ${total_pnl:,.2f}")

    print()
    print("="*70)
    print(f"Exported to: {output_csv}")
    print()

    # Show first 20 trades as preview
    print("\nPREVIEW (First 20 trades):")
    print("="*70)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    print(export_df.head(20).to_string(index=False))
    print()
    print(f"... (showing 20 of {len(export_df)} trades)")
    print()


if __name__ == "__main__":
    export_trade_status()
