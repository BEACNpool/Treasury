# Blockfrost fast snapshot (API mode)

This folder provides a **fast** (non-audit-grade) API snapshot using **Blockfrost**.

It exists to:
- reduce time-to-first-data while db-sync is still syncing,
- provide a second source for cross-checking,
- and keep publishing clearly labeled by provenance.

## Hard rules

- Do **not** publish anything unless it is **MAINNET**.
- API snapshots are always labeled `source_kind=blockfrost` and carry the API base URL + tip time.
- db-sync remains the audit-grade source-of-truth.

## Run

Set env:

```bash
export BLOCKFROST_PROJECT_ID=...  # secret
# optional
export BLOCKFROST_BASE=https://cardano-mainnet.blockfrost.io/api/v0
```

Generate outputs:

```bash
python3 scripts/blockfrost/treasury_snapshot.py --out outputs/blockfrost
```

Outputs:
- `outputs/blockfrost/status.json`
- `outputs/blockfrost/snapshot.csv`

## Publishing

Publishing should be an explicit step that copies files into `docs/outputs/` with a clear name.
Example:

- `docs/outputs/blockfrost/status.json`
- `docs/outputs/blockfrost/snapshot.csv`

Keep `docs/outputs/` **MAINNET-only**.
