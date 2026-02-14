#!/usr/bin/env python3
"""
Scrape all Project Catalyst proposers from projectcatalyst.io
Uses the internal Next.js API: /api/search?type=proposers&page=N

Data: 5,500+ proposers with funding info, project details, voting data.
Output: JSON (full data) + CSV (flattened summary)
"""

import json
import csv
import time
import urllib.request
import sys
from datetime import datetime

API_BASE = "https://projectcatalyst.io/api/search?type=proposers&page={}"
OUTPUT_JSON = "catalyst_proposers_full.json"
OUTPUT_CSV = "catalyst_proposers.csv"
ITEMS_PER_PAGE = 25
DELAY = 0.5  # seconds between requests (be nice to the server)


def fetch_page(page_num):
    """Fetch a single page of proposers."""
    url = API_BASE.format(page_num)
    req = urllib.request.Request(url, headers={
        "User-Agent": "CatalystTreasuryResearch/1.0",
        "Accept": "application/json"
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def parse_money(money_obj):
    """Convert money object {amount, exp, code} to float value."""
    if not money_obj or not money_obj.get("amount"):
        return 0.0
    amount = int(money_obj["amount"])
    exp = int(money_obj.get("exp", 0))
    return amount / (10 ** exp) if exp else float(amount)


def parse_money_list(money_list):
    """Parse a list of money objects, return dict by currency code."""
    if not money_list:
        return {}
    result = {}
    for m in money_list:
        code = m.get("code", "USD")
        result[code] = parse_money(m)
    return result


def flatten_proposer(item_data):
    """Flatten a proposer record for CSV output."""
    item = item_data.get("item", item_data)
    funding = item.get("funding", {})

    distributed = parse_money_list(funding.get("totalDistributedToDate", []))
    remaining = parse_money_list(funding.get("totalRemaining", []))
    requested = parse_money_list(funding.get("totalRequested", []))

    projects = item.get("projects", [])
    funded_project_names = [
        p["projectName"] for p in projects
        if p.get("projectStatus") in ("Complete", "InProgress", "Funded")
    ]
    all_project_names = [p["projectName"] for p in projects]

    return {
        "id": item.get("_id", ""),
        "name": item.get("name", ""),
        "username": item.get("username", ""),
        "ideascale_url": item.get("ideascaleUrl", ""),
        "catalyst_url": f"https://projectcatalyst.io/proposers/{item.get('username', '')}",
        "total_projects": item.get("totalProjects", 0),
        "funded_projects": item.get("fundedProjects", 0),
        "completed_projects": item.get("completedProjects", 0),
        "total_distributed_usd": distributed.get("USD", 0),
        "total_remaining_usd": remaining.get("USD", 0),
        "total_requested_usd": requested.get("USD", 0),
        "total_distributed_ada": distributed.get("$ADA", 0),
        "total_remaining_ada": remaining.get("$ADA", 0),
        "total_requested_ada": requested.get("$ADA", 0),
        "funded_project_names": "; ".join(funded_project_names),
        "all_project_names": "; ".join(all_project_names),
        "num_all_projects": len(all_project_names),
    }


def main():
    print(f"=== Project Catalyst Proposers Scraper ===")
    print(f"Started: {datetime.now().isoformat()}")
    print()

    # First request to get total count
    print("Fetching page 1 to get total count...")
    first_page = fetch_page(1)
    total_hits = first_page["data"]["search"]["hits"]
    total_pages = (total_hits + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    print(f"Total proposers: {total_hits}")
    print(f"Total pages: {total_pages}")
    print()

    # Collect all proposers
    all_proposers = []

    # Process first page
    items = first_page["data"]["search"]["results"]["proposers"]["items"]
    all_proposers.extend(items)
    print(f"Page 1/{total_pages}: {len(items)} proposers (total: {len(all_proposers)})")

    # Fetch remaining pages
    for page in range(2, total_pages + 1):
        time.sleep(DELAY)
        try:
            data = fetch_page(page)
            items = data["data"]["search"]["results"]["proposers"]["items"]
            all_proposers.extend(items)

            if page % 20 == 0 or page == total_pages:
                print(f"Page {page}/{total_pages}: {len(items)} proposers (total: {len(all_proposers)})")

        except Exception as e:
            print(f"Error on page {page}: {e}")
            # Retry once after a longer delay
            time.sleep(3)
            try:
                data = fetch_page(page)
                items = data["data"]["search"]["results"]["proposers"]["items"]
                all_proposers.extend(items)
                print(f"Page {page}/{total_pages}: RETRY OK, {len(items)} proposers")
            except Exception as e2:
                print(f"Page {page}: FAILED RETRY: {e2}")

        if not items:
            print(f"No more items at page {page}, stopping.")
            break

    print(f"\nTotal proposers scraped: {len(all_proposers)}")

    # Save full JSON
    print(f"\nSaving full JSON to {OUTPUT_JSON}...")
    full_data = {
        "metadata": {
            "source": "https://projectcatalyst.io/search?type=proposers",
            "api_endpoint": "https://projectcatalyst.io/api/search?type=proposers&page=N",
            "scraped_at": datetime.now().isoformat(),
            "total_proposers": len(all_proposers),
        },
        "proposers": [p.get("item", p) for p in all_proposers]
    }
    with open(OUTPUT_JSON, "w") as f:
        json.dump(full_data, f, indent=2)
    print(f"  Saved {OUTPUT_JSON}")

    # Save flattened CSV
    print(f"Saving CSV to {OUTPUT_CSV}...")
    flat_data = [flatten_proposer(p) for p in all_proposers]

    if flat_data:
        fieldnames = list(flat_data[0].keys())
        with open(OUTPUT_CSV, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(flat_data)
        print(f"  Saved {OUTPUT_CSV}")

    # Print summary stats
    funded = sum(1 for p in flat_data if p["funded_projects"] > 0)
    completed = sum(1 for p in flat_data if p["completed_projects"] > 0)
    total_dist_usd = sum(p["total_distributed_usd"] for p in flat_data)
    total_req_usd = sum(p["total_requested_usd"] for p in flat_data)

    print(f"\n=== Summary ===")
    print(f"Total proposers:        {len(flat_data):,}")
    print(f"With funded projects:   {funded:,}")
    print(f"With completed projects:{completed:,}")
    print(f"Total distributed (USD):${total_dist_usd:,.2f}")
    print(f"Total requested (USD):  ${total_req_usd:,.2f}")
    print(f"\nDone! {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
