# Flag taxonomy (v1)

This project uses **flags** for analysis and triage.

**Flags are not accusations.**

A flag is:
- a *rule-based* signal,
- with explicit thresholds,
- backed by receipts,
- with false-positive notes,
- and a "clears if…" clause.

## 1) Severity colors (single meaning)

Colors represent **urgency/severity** only.

- **RED — High risk / urgent review**
  - Triggered by multiple independent signals, or a single strong on-chain signal with high confidence.

- **ORANGE — Needs info**
  - Missing disclosures/receipts or ambiguous behavior that prevents a fair assessment.

- **YELLOW — Watch**
  - Non-alarming but notable patterns worth monitoring.

- **GREEN — Cleared / resolved**
  - A previously raised flag that has been cleared by evidence.

## 2) Evidence/source type (separate from severity)

Source type is indicated via **icons/shapes** (not colors) to prevent confusion:

- **● On-chain** — ledger facts (db-sync, node, chain data)
- **■ Off-chain** — program registries, repos, websites (Catalyst, Intersect, etc.)
- **▲ Heuristic** — clustering/attribution guesses (always lower confidence)

## 3) Confidence

Confidence reflects evidence quality (not "how bad it feels"):

- **High**: direct receipts + robust query
- **Medium**: partial receipts or reasonable inference
- **Low**: heuristic-only or incomplete observations

## 4) Canonical flag record format

Every emitted flag must include:

- `flag_id` (stable ID)
- `entity_id` (stable entity/recipient ID)
- `severity` (red|orange|yellow|green)
- `source_kind` (onchain|offchain|heuristic)
- `confidence` (high|medium|low)
- `title`
- `definition` (thresholds)
- `evidence` (links + tx hashes + query references)
- `false_positives` (common explanations)
- `clears_if` (what evidence clears the flag)
- `observed_at` (timestamp)
- `data_tip` (tip time/height for the dataset used)

## 5) Publication policy

- Publish **flags + receipts** as the primary output.
- Any "AI summary" must be **criteria-based** and link directly to the underlying flags.
