# Treasury — Cardano Treasury Inflows/Outflows (Open Research)

[![Validate Outputs](https://github.com/BEACNpool/Treasury/actions/workflows/validate.yml/badge.svg)](https://github.com/BEACNpool/Treasury/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Goal:** produce an auditable, reproducible view of Cardano treasury **inflows** (fees + expansion + other) and **outflows** (withdrawals / distributions), with multiple levels of rigor.

| Mode | Source | Use case |
|------|--------|----------|
| **Audit path** | `cardano-db-sync` + PostgreSQL | Gold-standard, reproducible SQL |
| **Fast path** | Blockfrost API | Quick iteration while db-sync syncs |

This repo publishes clean CSV exports, methodology + caveats, and source receipts.

🔗 **[Live Dashboard](https://beacnpool.github.io/Treasury/)** · [Methodology](docs/methodology.md) · [Data Dictionary](docs/data_dictionary.md) · [Sources](docs/sources.md)

## Outputs

| File | Description |
|------|-------------|
| `outputs/epoch_treasury_fees.csv` | Per-epoch treasury flows (lovelace + ADA) |
| `outputs/year_treasury_fees.csv` | Calendar-year aggregation |
| `outputs/status.json` | Machine-readable provenance (network, tip, timestamp) |
| `outputs/treasury.duckdb` | Local analytics index (optional) |

## Principles

- **Evidence-first:** every computed number traces to a source query + timestamp.
- **Prefer on-chain truths** over off-chain narratives.
- **No secrets committed.** API keys/tokens belong in local credential stores.
- **Mainnet-only publishing.** All scripts refuse non-mainnet by default.

## Quickstart

### 1. db-sync mode (audit-grade)

Requires a synced `cardano-db-sync` PostgreSQL database.

```bash
# Set your db-sync connection string
export DATABASE_URL="postgresql://USER:PASSWORD@HOST:5432/cexplorer"

# Run the pipeline
cd scripts/dbsync
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python treasury_fees.py --dsn "$DATABASE_URL" --out ../../outputs
```

### 2. Blockfrost mode (fast snapshot)

Useful while db-sync is still syncing.

```bash
export BLOCKFROST_PROJECT_ID="your-mainnet-project-id"

python3 scripts/blockfrost/treasury_snapshot.py --out outputs/blockfrost
```

### 3. Validate outputs

Run reconciliation checks to verify data integrity:

```bash
pip install pandas --break-system-packages  # or use a venv
python3 scripts/validate.py --epoch outputs/epoch_treasury_fees.csv
```

### 4. Plot yearly chart

```bash
python3 scripts/plot_yearly.py \
  --in outputs/year_treasury_fees.csv \
  --out outputs/year_treasury_fees.png
```

### 5. Build a local DuckDB index

```bash
pip install -r requirements.txt  # or use a venv
python3 scripts/index_duckdb.py --out outputs/treasury.duckdb

# Query it
duckdb outputs/treasury.duckdb "SELECT * FROM year_overview LIMIT 5"
```

### 6. Publish to GitHub Pages

After generating mainnet outputs:

```bash
bash scripts/publish.sh
```

This copies validated outputs into `docs/outputs/` for the live dashboard.

## Dashboard

The live dashboard at `docs/index.html` is served via GitHub Pages. It provides:

- **Yearly overview chart** — fees, estimated inflows, withdrawals, treasury delta
- **Fees vs Withdrawals** — bar chart comparison
- **Treasury balance** — absolute balance over time (epoch-level)
- **Interactive data table** with CSV download

See `docs/methodology.md` for caveats and reconciliation notes.

## Project structure

```
Treasury/
├── scripts/
│   ├── dbsync/           # Audit-grade pipeline (SQL + Python)
│   ├── blockfrost/       # Fast API snapshot
│   ├── validate.py       # Data reconciliation checks
│   ├── publish.sh        # Publish outputs to docs/ for Pages
│   ├── plot_yearly.py    # Matplotlib chart generation
│   └── index_duckdb.py   # DuckDB analytics index builder
├── outputs/              # Generated data (CSV, PNG, JSON)
├── docs/                 # GitHub Pages dashboard + methodology
│   ├── index.html        # Dashboard entry point
│   ├── outputs/          # Published mainnet data (for Pages)
│   └── *.md              # Methodology, data dictionary, etc.
└── .github/workflows/    # CI validation
```

## Contributing

Contributions welcome. Please open an issue first for significant changes.

## License

[MIT](LICENSE)
