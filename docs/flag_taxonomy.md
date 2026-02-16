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

## 6) Catalyst-oriented flags (v0 candidates)

These are proposed / early flags that can be computed from the exported Catalyst receipts dataset.
They are designed to be *review signals*, not labels.

> **Important limitation:** the Catalyst export does not reliably provide payout addresses/wallets.
> Any “same wallet under different names” detection must be treated as **heuristic** unless we can link to a payment address/tx.

### F-CAT-001 — High concentration (single proposer)
- **Severity:** yellow → orange (if extreme)
- **Source:** offchain
- **Definition:** a single proposer’s `distributedToDate` sum exceeds a threshold (eg: ≥ ₳500k, ≥ ₳1M, ≥ ₳5M).
- **False positives:** legitimate large vendors; umbrella orgs; multi-team initiatives.
- **Clears if:** proposer provides a breakdown of deliverables + maintenance plan + public repos + usage metrics.

### F-CAT-002 — Many paid proposals for content-like deliverables
- **Severity:** yellow
- **Source:** heuristic (keyword)
- **Definition:** proposer has ≥ N paid proposals whose titles/tags match content buckets (marketing/social/video/translation/etc.).
- **False positives:** real-world events; regional adoption; non-software deliverables.
- **Clears if:** receipts show measurable adoption outcomes + reusable assets.

### F-CAT-003 — Cancelled but paid
- **Severity:** orange
- **Source:** offchain
- **Definition:** `projectStatus == Cancelled` AND `distributedToDate > 0`.
- **False positives:** partial work delivered; milestone-based payments.
- **Clears if:** receipts show what was delivered for the paid amount.

### F-CAT-004 — Shared avatar/identity indicators across proposers (heuristic)
- **Severity:** yellow
- **Source:** heuristic
- **Definition:** multiple proposer records share the same **non-default** `avatarUrl` while having different usernames.
  - Default IdeaScale avatars (eg `static.ideascaleapp.eu/images/avatar/...`) are excluded.
- **False positives:** org branding reused across accounts.
- **Clears if:** relationship is disclosed (same org/team) or avatars are updated to unique identifiers.

### F-CAT-005 — Duplicate / near-duplicate project names across proposers (heuristic)
- **Severity:** yellow
- **Source:** heuristic
- **Definition:** highly similar project names appear under multiple distinct proposers.
- **False positives:** common phrases; shared challenge naming.
- **Clears if:** receipts clarify team relationships or distinct deliverables.
