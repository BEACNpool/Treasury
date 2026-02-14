#!/usr/bin/env python3
"""Generate publication-quality yearly treasury charts.

Usage:
  python scripts/plot_yearly.py --in outputs/year_treasury_fees.csv --out outputs/year_treasury_fees.png
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

# Style
plt.rcParams.update({
    'figure.facecolor': '#0b0f17',
    'axes.facecolor': '#111827',
    'axes.edgecolor': '#233044',
    'axes.labelcolor': '#9fb0c0',
    'xtick.color': '#9fb0c0',
    'ytick.color': '#9fb0c0',
    'text.color': '#e6edf3',
    'grid.color': '#233044',
    'grid.alpha': 0.5,
    'legend.facecolor': '#111827',
    'legend.edgecolor': '#233044',
    'font.size': 11,
})

COLORS = {
    'fees': '#60a5fa',
    'inflow': '#34d399',
    'withdrawals': '#f87171',
    'delta': '#fbbf24',
}


def ada_formatter(x, p):
    if abs(x) >= 1e9:
        return f'{x/1e9:.1f}B'
    if abs(x) >= 1e6:
        return f'{x/1e6:.0f}M'
    if abs(x) >= 1e3:
        return f'{x/1e3:.0f}K'
    return f'{x:.0f}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', required=True, help='year_treasury_fees.csv')
    ap.add_argument('--out', required=True, help='output png path')
    args = ap.parse_args()

    df = pd.read_csv(args.inp)

    # Compute withdrawals if needed
    if 'withdrawals_ada' not in df.columns:
        df['withdrawals_ada'] = df.get('mir_treasury_payments_ada', 0) + df.get('conway_enacted_withdrawals_ada', 0)

    fig, axes = plt.subplots(2, 1, figsize=(12, 9), gridspec_kw={'height_ratios': [3, 2]})

    # Chart 1: Lines
    ax1 = axes[0]
    ax1.plot(df['year'], df['fees_ada'], marker='o', markersize=5, label='Fees', color=COLORS['fees'], linewidth=2)
    ax1.plot(df['year'], df['inflow_fees_plus_reserves_ada'], marker='s', markersize=5, label='Est. Inflow (fees+expansion)', color=COLORS['inflow'], linewidth=2)
    ax1.plot(df['year'], df['treasury_delta_ada'], marker='^', markersize=5, label='Treasury Δ', color=COLORS['delta'], linewidth=2)
    ax1.plot(df['year'], df['withdrawals_ada'], marker='D', markersize=5, label='Withdrawals', color=COLORS['withdrawals'], linewidth=2)
    ax1.set_title('Cardano Treasury: Yearly Flows', fontsize=16, fontweight='bold', pad=12)
    ax1.set_ylabel('ADA')
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(ada_formatter))
    ax1.legend(loc='upper left', fontsize=10)
    ax1.grid(True)

    # Chart 2: Bar comparison
    ax2 = axes[1]
    x = df['year']
    w = 0.35
    ax2.bar(x - w / 2, df['fees_ada'], w, label='Fees', color=COLORS['fees'], alpha=0.85)
    ax2.bar(x + w / 2, df['withdrawals_ada'], w, label='Withdrawals', color=COLORS['withdrawals'], alpha=0.85)
    ax2.set_title('Fees vs Withdrawals', fontsize=14, fontweight='bold', pad=10)
    ax2.set_xlabel('Year')
    ax2.set_ylabel('ADA')
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(ada_formatter))
    ax2.legend(loc='upper left', fontsize=10)
    ax2.grid(True)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(pad=2)
    fig.savefig(args.out, dpi=150, bbox_inches='tight')
    print(f'wrote {args.out}')


if __name__ == '__main__':
    main()
