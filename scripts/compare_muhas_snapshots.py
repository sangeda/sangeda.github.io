#!/usr/bin/env python3
"""Compare a new Observatory raw snapshot with the previous one.

Reports aggregate counts only (no titles), for the run annotations:
works added and removed, and for removed works whether OpenAlex
  - no longer returns them (deleted or merged),
  - still holds them without a MUHAS lineage authorship (affiliation re-linked),
  - still links them to MUHAS (left the set for another reason, e.g. date).
Removed works are also counted against the backdated-deposit rule used by the
analyses: repository-hosted (PubMed exempt), created in or after 2026, dated
at least 3 years before creation.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
import urllib.parse
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_muhas_observatory as obs  # noqa: E402

BATCH = 50


def load(path: Path) -> dict[str, dict]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return {obs.short_id(w.get("id")): w for w in map(json.loads, stream)}


is_backdated_deposit = obs.is_backdated_deposit


def has_muhas(work: dict) -> bool:
    return any(
        obs.OPENALEX_ID in (inst.get("lineage") or []) or obs.short_id(inst.get("id")) == obs.OPENALEX_ID
        for a in work.get("authorships") or [] for inst in a.get("institutions") or []
    )


def current_status(ids: list[str]) -> Counter:
    """Look the removed works up again (batched; list results suffice for presence and affiliation)."""
    found: dict[str, dict] = {}
    for i in range(0, len(ids), BATCH):
        chunk = ids[i:i + BATCH]
        query = urllib.parse.urlencode({
            "filter": "openalex:" + "|".join(chunk),
            "select": "id,authorships,publication_date",
            "per-page": BATCH,
        })
        for work in obs.api_json(f"https://api.openalex.org/works?{query}").get("results", []):
            found[obs.short_id(work.get("id"))] = work
        time.sleep(0.12)
    status = Counter()
    for wid in ids:
        work = found.get(wid)
        if work is None:
            status["not_returned_deleted_or_merged"] += 1
        elif not has_muhas(work):
            status["no_muhas_affiliation_now"] += 1
        else:
            status["still_muhas_other_reason"] += 1
    return status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("previous", type=Path)
    parser.add_argument("current", type=Path)
    parser.add_argument("--no-api", action="store_true", help="skip re-querying removed works")
    args = parser.parse_args()
    old, new = load(args.previous), load(args.current)
    removed = sorted(set(old) - set(new))
    added = sorted(set(new) - set(old))
    report = {
        "previous_works": len(old),
        "current_works": len(new),
        "added": len(added),
        "removed": len(removed),
        "removed_matching_backdated_rule": sum(is_backdated_deposit(old[w]) for w in removed),
        "backdated_rule_previous": sum(map(is_backdated_deposit, old.values())),
        "backdated_rule_current": sum(map(is_backdated_deposit, new.values())),
        "added_matching_backdated_rule": sum(is_backdated_deposit(new[w]) for w in added),
        "removed_by_source_type": dict(Counter(
            ((old[w].get("primary_location") or {}).get("source") or {}).get("type") or "none" for w in removed
        ).most_common(5)),
    }
    if removed and not args.no_api:
        report["removed_status_now"] = dict(current_status(removed))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
