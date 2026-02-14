# Off-chain dataset: Project Catalyst (scraped)

This repo publishes a **verbatim scrape** of Project Catalyst proposer + project data from the Catalyst website.

## Provenance

- Human-facing page: https://projectcatalyst.io/search?type=proposers
- Underlying API used by the site (Next.js route):
  - https://projectcatalyst.io/api/search?type=proposers&page=N
- Scrape script (archived in-repo): `scripts/catalyst_scrape_proposers.py`
- Raw published dataset (compressed):
  - `docs/outputs/offchain/catalyst/catalyst_proposers_full.json.gz`
- Checksums:
  - `docs/outputs/offchain/catalyst/manifest.sha256`

**Important:** This is **off-chain** data. It is useful context and a rich index of recipients/projects, but it is not ledger-truth.

## What’s in the scrape (high-level)

The published JSON has the form:

- `metadata`
  - `source` (page URL)
  - `api_endpoint` (route pattern)
  - `scraped_at` (timestamp)
  - `total_proposers`
- `proposers[]`
  - proposer identity + totals
  - nested `projects[]` with per-project funding + status + voting info

## Proposer fields (observed)

Each `proposers[]` record includes (at least):

- `_id` (proposer id)
- `name`
- `username`
- `avatarUrl`
- `ideascaleUrl`
- `totalProjects`
- `fundedProjects`
- `completedProjects`
- `funding`
  - `totalDistributedToDate[]` — money objects (often USD)
  - `totalRemaining[]`
  - `totalRequested[]`
- `projects[]` — see next section

### Money object format

Funding values appear as objects like:

```json
{"amount":"300000000000","exp":6,"code":"$ADA"}
```

Interpretation: `value = int(amount) / 10^exp`.

## Project fields (observed)

Each proposer contains `projects[]`, where each project includes (at least):

- `_id` (project id)
- `_fundingId` (funding id)
- `projectName`
- `projectSlug`
- `projectStatus` (e.g., Completed)
- `fundId` (numeric fund identifier)
- `challenge`
  - `_id`
  - `fundId`
  - `name`
  - `slug`
- `country`, `continent`
- `horizonGroup`
- `tags[]`
- `funding`
  - `distributedToDate` (money object; often $ADA)
  - `remaining`
  - `requested`
- `updatedAt` (epoch ms; used only as a **proxy** timestamp in derived outputs)
- `voting` (nested voting info)
- `leftoverVoting` (nested)
- `completed` (boolean)

## Derived/published tables (for browsing)

We publish small, reviewable derivatives:

- `docs/outputs/offchain/catalyst/summary.json`
- `docs/outputs/offchain/catalyst/top_recipients.csv`
- `docs/outputs/offchain/catalyst/yearly_distributions.csv` (proxy series; bucketed by `updatedAt` year)

## How this data is used here

- As **off-chain context** for recipients/projects.
- As inputs to **flags** (signals, not accusations): concentration, completion ratios, repeated funding, etc.
- Never as sole evidence of on-chain fund flows.
