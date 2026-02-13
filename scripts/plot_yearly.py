#!/usr/bin/env python3
import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ap=argparse.ArgumentParser()
ap.add_argument('--in', dest='inp', required=True, help='year_treasury_fees.csv')
ap.add_argument('--out', required=True, help='output png path')
args=ap.parse_args()

df=pd.read_csv(args.inp)

fig, ax = plt.subplots(figsize=(10,5))
ax.plot(df['year'], df['fees_ada'], label='Fees (ADA)')
ax.plot(df['year'], df['inflow_fees_plus_reserves_ada'], label='Est. inflow to treasury (fees+expansion)')
ax.plot(df['year'], df['treasury_delta_ada'], label='Treasury Δ (ADA)')
ax.set_title('Cardano Treasury: inflows vs balance change (yearly)')
ax.set_xlabel('Year')
ax.set_ylabel('ADA')
ax.grid(True, alpha=0.3)
ax.legend()
Path(args.out).parent.mkdir(parents=True, exist_ok=True)
fig.tight_layout()
fig.savefig(args.out, dpi=150)
print('wrote', args.out)
