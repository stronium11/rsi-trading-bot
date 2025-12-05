#!/usr/bin/env python3
"""
Re-run Phase 3 with T2 > T1 constraint
Tests T2 at +18%, +20%, +22%, +25% (all higher than T1 of +15%)
"""

from iterative_optimizer import IterativeOptimizer
import time


def rerun_phase3_corrected():
    """Re-run Phase 3 with proper T2 > T1 constraint"""

    optimizer = IterativeOptimizer()
    optimizer.load_data()

    # Best rules from Phase 1 & 2
    best_rules = {
        'initial_stop_pct': 7,
        'target1_pct': 15,
        'target1_size': 70,
        'target2_pct': 20,  # Will be varied
        'target2_size': 25,  # Will be varied
        'target3_pct': 50,
        'breakeven_trigger_pct': 5,
        'max_hold_days': 120,
        'use_trailing_stop': False
    }

    print("\n" + "="*70)
    print("RE-RUNNING PHASE 3: OPTIMIZING TARGET 2 (CORRECTED)")
    print("="*70)
    print("\nConstraint: T2 must be > T1 (+15%)")
    print("Testing T2 targets: +18%, +20%, +22%, +25%")
    print("Testing T2 sizing: 15%, 20%, 25%, 30%")
    print("\nUsing cached price data for fast testing...\n")

    target2_tests = [18, 20, 22, 25]
    sizing2_tests = [15, 20, 25, 30]
    results = []

    for target_pct in target2_tests:
        for size_pct in sizing2_tests:
            rules = best_rules.copy()
            rules['target2_pct'] = target_pct
            rules['target2_size'] = size_pct

            print(f"Testing T2 +{target_pct}% ({size_pct}%)...", end=' ')
            start = time.time()

            result = optimizer.test_rule_set(rules, f"T2 +{target_pct}% ({size_pct}%)")
            results.append(result)

            elapsed = time.time() - start
            print(f"P&L: ${result['total_pnl']:,.2f}, WR: {result['win_rate']:.1f}% ({elapsed:.1f}s)")

    # Find best
    best = max(results, key=lambda x: x['total_pnl'])

    print(f"\n{'='*70}")
    print("CORRECTED PHASE 3 RESULTS")
    print(f"{'='*70}")
    print(f"\n🏆 BEST TARGET 2: +{best['rules']['target2_pct']}% closing {best['rules']['target2_size']}%")
    print(f"   Total P&L: ${best['total_pnl']:,.2f}")
    print(f"   Win Rate: {best['win_rate']:.1f}%")
    print(f"   Profit Factor: {best['profit_factor']:.2f}")

    # Compare to original Phase 3 winner
    original_best_pnl = 11885.94  # T2 at +15% (30%)
    improvement = best['total_pnl'] - original_best_pnl

    print(f"\n📊 COMPARISON TO ORIGINAL:")
    print(f"   Original best (T2 +15%, 30%): ${original_best_pnl:,.2f}")
    print(f"   Corrected best (T2 +{best['rules']['target2_pct']}%, {best['rules']['target2_size']}%): ${best['total_pnl']:,.2f}")

    if improvement > 0:
        print(f"   ✅ Corrected is better by: +${improvement:,.2f}")
    elif improvement < 0:
        print(f"   ❌ Original was better by: ${abs(improvement):,.2f}")
        print(f"   Note: This suggests T2=T1 might be optimal (close all at +15%)")
    else:
        print(f"   Same performance")

    # Show top 3 configurations
    results_sorted = sorted(results, key=lambda x: x['total_pnl'], reverse=True)
    print(f"\n📈 TOP 3 CONFIGURATIONS:")
    for i, result in enumerate(results_sorted[:3], 1):
        print(f"   #{i}: T2 +{result['rules']['target2_pct']}% ({result['rules']['target2_size']}%) "
              f"→ ${result['total_pnl']:,.2f}")

    # Final recommendation
    print(f"\n{'='*70}")
    print("RECOMMENDATION")
    print(f"{'='*70}")

    if best['total_pnl'] > original_best_pnl:
        print(f"\n✅ Use corrected T2: +{best['rules']['target2_pct']}% closing {best['rules']['target2_size']}%")
        print(f"   This is ${improvement:,.2f} better than T2=T1 approach")
    else:
        print(f"\n⚠️  Original configuration (T2 at +15%) performs better!")
        print(f"   This suggests the optimal strategy is:")
        print(f"   - Close 70% at first +15% touch (T1)")
        print(f"   - Close remaining 30% shortly after at +15% (T2)")
        print(f"   - This is effectively 'close everything around +15%'")
        print(f"\n   Alternative interpretation:")
        print(f"   - Simplify to single exit: Close 100% at +15%")
        print(f"   - Would need separate test to confirm")

    return best


if __name__ == "__main__":
    rerun_phase3_corrected()
