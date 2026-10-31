#!/usr/bin/env python3
"""Fetch full OpenAlex work records for a list of DOIs or OpenAlex work ids.

A read-only helper for bibliometric comparisons (bibpysona). It is separate
from the Observatory build and changes nothing on the site.

Input: a text file, one identifier per line -- a DOI ("10.1/abc",
"https://doi.org/10.1/abc") or an OpenAlex work id ("W123", full URL).
Blank lines and lines starting with '#' are ignored.

Output (in --out):
  <name>.jsonl.gz      one full work record per line, as OpenAlex returns it
  <name>_summary.json  counts, and the identifiers OpenAlex did not return

Lookups are batched (50 identifiers per request, OpenAlex's OR-filter limit).
List results can carry at most 100 authorships, so any work returned with
100 is fetched again on its own (the single-work endpoint returns them all).
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = "muhas-publications-observatory/1.0 (openalex_lookup)"
API = "https://api.openalex.org/works"
BATCH = 50


def api_json(url: str, attempts: int = 5) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.load(response)
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(min(30, 2 ** attempt))
    raise RuntimeError("OpenAlex request failed")


def norm_doi(value: str) -> str:
    d = value.strip().lower()
    d = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", d)
    return d.rstrip(" .;,")


def parse_ids(lines: list[str]) -> tuple[list[str], list[str]]:
    dois, works = [], []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        tail = line.rstrip("/").rsplit("/", 1)[-1]
        if re.fullmatch(r"[Ww]\d+", tail) and "doi" not in line.lower():
            works.append(tail.upper())
        else:
            dois.append(norm_doi(line))
    return list(dict.fromkeys(dois)), list(dict.fromkeys(works))


def fetch_batch(field: str, values: list[str]) -> list[dict]:
    query = urllib.parse.urlencode({"filter": f"{field}:" + "|".join(values), "per-page": 200})
    return api_json(f"{API}?{query}").get("results", [])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("ids_file", type=Path)
    parser.add_argument("--out", type=Path, default=Path("lookup_out"))
    args = parser.parse_args()

    dois, work_ids = parse_ids(args.ids_file.read_text(encoding="utf-8").splitlines())
    found: dict[str, dict] = {}
    for field, values in (("doi", dois), ("openalex", work_ids)):
        for i in range(0, len(values), BATCH):
            for work in fetch_batch(field, values[i:i + BATCH]):
                found[work["id"]] = work
            time.sleep(0.15)

    refetched = 0
    for wid, work in list(found.items()):
        if len(work.get("authorships") or []) >= 100:
            found[wid] = api_json(f"{API}/{wid.rsplit('/', 1)[-1]}")
            refetched += 1
            time.sleep(0.15)

    got_dois = {norm_doi(w.get("doi") or "") for w in found.values()}
    got_ids = {w["id"].rsplit("/", 1)[-1] for w in found.values()}
    name = args.ids_file.stem
    args.out.mkdir(parents=True, exist_ok=True)
    with gzip.open(args.out / f"{name}.jsonl.gz", "wt", encoding="utf-8") as f:
        for work in found.values():
            f.write(json.dumps(work, ensure_ascii=False) + "\n")
    summary = {
        "input": str(args.ids_file), "dois_requested": len(dois), "work_ids_requested": len(work_ids),
        "works_returned": len(found), "refetched_for_full_authorships": refetched,
        "dois_not_found": sorted(d for d in dois if d not in got_dois),
        "work_ids_not_found": sorted(w for w in work_ids if w not in got_ids),
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (args.out / f"{name}_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if not k.endswith("not_found")}, indent=2))
    print(f"not found: {len(summary['dois_not_found'])} DOIs, {len(summary['work_ids_not_found'])} work ids")


if __name__ == "__main__":
    main()
