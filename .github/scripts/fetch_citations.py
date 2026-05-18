"""Refresh the citation-count badge JSON consumed by shields.io's endpoint API.

Queries two free, no-auth public APIs and keeps the larger of the two counts:

  * Semantic Scholar (api.semanticscholar.org) — broader coverage, typically
    closer to Google Scholar's number.
  * Crossref (api.crossref.org) — conservative but very reliable.

The resulting JSON is written to `.github/badges/citations.json` in the schema
required by https://shields.io/badges/endpoint-badge. The README references it
via:

    https://img.shields.io/endpoint?url=<RAW_URL_TO_JSON>

If both APIs fail or report zero, the existing badge is left unchanged so a
transient blip never blanks the count.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DOI = "10.1016/j.scs.2026.107491"
TIMEOUT = 15  # seconds — both APIs are usually < 1s
USER_AGENT = "TI-acs-public-badge-bot (+https://github.com/eCal-UCB/TI-acs-public)"


def _fetch(url: str) -> dict | None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.load(resp)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            json.JSONDecodeError) as e:
        print(f"  [warn] {url}: {type(e).__name__}: {e}", file=sys.stderr)
        return None


def semantic_scholar_count(doi: str) -> int | None:
    """Return citationCount from the Semantic Scholar Graph API."""
    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=citationCount"
    data = _fetch(url)
    if data is None:
        return None
    n = data.get("citationCount")
    if isinstance(n, int) and n >= 0:
        return n
    return None


def crossref_count(doi: str) -> int | None:
    """Return is-referenced-by-count from Crossref."""
    url = f"https://api.crossref.org/works/{doi}"
    data = _fetch(url)
    if data is None:
        return None
    n = data.get("message", {}).get("is-referenced-by-count")
    if isinstance(n, int) and n >= 0:
        return n
    return None


def make_badge_payload(count: int) -> dict:
    return {
        "schemaVersion": 1,
        "label": "cited by",
        "message": str(count),
        "color": "4285F4",
        "namedLogo": "googlescholar",
        "logoColor": "white",
        "cacheSeconds": 3600,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=".github/badges/citations.json",
                        help="Path of the badge-endpoint JSON file to update.")
    parser.add_argument("--doi", default=DOI, help="DOI to look up.")
    args = parser.parse_args()

    print(f"Looking up citations for DOI: {args.doi}")
    s2 = semantic_scholar_count(args.doi)
    cr = crossref_count(args.doi)
    print(f"  Semantic Scholar: {s2}")
    print(f"  Crossref:         {cr}")

    candidates = [n for n in (s2, cr) if n is not None]
    if not candidates:
        print("Both APIs failed — leaving existing badge untouched.")
        return 0  # not a build failure; cron will retry

    new_count = max(candidates)

    # Read existing count (if any) to avoid pointless commits.
    old_count: int | None = None
    if os.path.exists(args.output):
        try:
            with open(args.output) as f:
                old_count = int(json.load(f).get("message", -1))
        except (json.JSONDecodeError, ValueError, OSError):
            old_count = None

    # Don't regress past a higher previous value — guard against API hiccups.
    if old_count is not None and new_count == 0 and old_count > 0:
        print(f"  Both APIs returned 0 but cache shows {old_count}; keeping cache.")
        return 0

    if old_count == new_count:
        print(f"  Count unchanged at {new_count}; not rewriting.")
        return 0

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(make_badge_payload(new_count), f, indent=2)
        f.write("\n")
    print(f"  Wrote {args.output} with count = {new_count} (was {old_count}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
