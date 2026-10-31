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

Title mode (--titles file.csv with columns ref,title,year,first_author):
each row is searched by title within year +/- 1. The best hit is accepted only
when the normalised token-sort title similarity is >= 93 and the Scopus first
author's surname matches the hit's first authorship. Outputs are keyed by ref
and never contain the input titles:
  <name>.jsonl.gz          accepted records, each with "_lookup_ref"
  <name>_matches.csv       ref,status,openalex_id,score,best_candidate_id,best_candidate_score
  <name>_summary.json      counts, retrieval time, not-found reasons by ref
Nothing in the log identifies a title: progress is printed by ref only.

Set OPENALEX_API_KEY to send an API key with every request.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = "muhas-publications-observatory/1.0 (openalex_lookup)"
API = "https://api.openalex.org/works"
BATCH = 50


TITLE_THRESHOLD = 93.0


def with_api_key(url: str) -> str:
    key = os.environ.get("OPENALEX_API_KEY", "").strip()
    return f"{url}{'&' if '?' in url else '?'}{urllib.parse.urlencode({'api_key': key})}" if key else url


def api_json(url: str, attempts: int = 5) -> dict:
    """Errors never include the URL, which may carry a title or the key."""
    request = urllib.request.Request(with_api_key(url), headers={"User-Agent": USER_AGENT})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                raise RuntimeError(f"OpenAlex refused the request (HTTP {error.code}); check OPENALEX_API_KEY") from None
            if attempt == attempts - 1:
                raise RuntimeError(f"OpenAlex HTTP {error.code} after {attempts} attempts") from None
            time.sleep(min(60, 5 * 2 ** attempt) if error.code == 429 else min(30, 2 ** attempt))
        except Exception as error:
            if attempt == attempts - 1:
                raise RuntimeError(f"OpenAlex request failed ({type(error).__name__})") from None
            time.sleep(min(30, 2 ** attempt))
    raise RuntimeError("OpenAlex request failed")


def fold(text: str) -> str:
    """Lower-case, fold accents, replace punctuation with spaces, collapse spaces."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = re.sub(r"[^\w\s]|_", " ", text)
    return " ".join(text.split())


def token_sort_ratio(a: str, b: str) -> float:
    a, b = " ".join(sorted(fold(a).split())), " ".join(sorted(fold(b).split()))
    try:
        from rapidfuzz import fuzz
        return float(fuzz.ratio(a, b))
    except ImportError:
        from difflib import SequenceMatcher
        return 100.0 * SequenceMatcher(None, a, b).ratio()


def scopus_surname(first_author: str) -> str:
    """'Chan S.-Y.' -> 'chan'; 'Mohamed-Ahmed O.' -> 'mohamed ahmed'; 'Lüdtke U.M.' -> 'ludtke'."""
    tokens = (first_author or "").split()
    while len(tokens) > 1 and re.fullmatch(r"(?:[^\W\d_]{1,2}\.-?)+", tokens[-1]):
        tokens.pop()
    return fold(" ".join(tokens))


def surname_matches(surname: str, display_name: str) -> bool:
    """True if the surname's tokens appear contiguously in the author's name."""
    if not surname:
        return False
    want, have = surname.split(), fold(display_name).split()
    return any(have[i:i + len(want)] == want for i in range(len(have) - len(want) + 1))


def first_author_name(work: dict) -> str:
    authorships = work.get("authorships") or []
    first = next((a for a in authorships if a.get("author_position") == "first"), authorships[0] if authorships else {})
    return (first.get("author") or {}).get("display_name") or ""


def match_title(row: dict) -> dict:
    year = int(row["year"])
    query = urllib.parse.urlencode({
        "search": fold(row["title"]),  # folded: no punctuation or upper-case AND/OR/NOT operators
        "filter": f"publication_year:{year - 1}-{year + 1}",
        "per-page": 5,
    })
    hits = api_json(f"{API}?{query}").get("results", [])
    surname = scopus_surname(row["first_author"])
    scored = sorted(
        ((token_sort_ratio(row["title"], h.get("title") or h.get("display_name") or ""), h) for h in hits),
        key=lambda pair: -pair[0],
    )
    best_score, best = scored[0] if scored else (0.0, None)
    accepted = next(((s, h) for s, h in scored if s >= TITLE_THRESHOLD and surname_matches(surname, first_author_name(h))), None)
    if accepted:
        score, hit = accepted
        return {"status": "found", "work": hit, "score": round(score, 1),
                "best_id": hit["id"].rsplit("/", 1)[-1], "best_score": round(score, 1), "reason": ""}
    if best is None:
        reason = "no_results"
    elif best_score < TITLE_THRESHOLD:
        reason = "title_below_threshold"
    else:
        reason = "first_author_surname_mismatch"
    return {"status": "not_found", "work": None, "score": "",
            "best_id": best["id"].rsplit("/", 1)[-1] if best else "", "best_score": round(best_score, 1) if best else "",
            "reason": reason}


def run_titles(path: Path, out: Path) -> None:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    name = path.stem
    out.mkdir(parents=True, exist_ok=True)
    matches, records, reasons, refetched = [], [], {}, 0
    for i, row in enumerate(rows, 1):
        result = match_title(row)
        if result["work"] is not None:
            work = result["work"]
            if len(work.get("authorships") or []) >= 100:
                work = api_json(f"{API}/{work['id'].rsplit('/', 1)[-1]}")
                refetched += 1
                time.sleep(0.15)
            work["_lookup_ref"] = row["ref"]
            records.append(work)
        else:
            reasons[row["ref"]] = result["reason"]
        matches.append({
            "ref": row["ref"], "status": result["status"],
            "openalex_id": result["work"]["id"].rsplit("/", 1)[-1] if result["work"] else "",
            "score": result["score"], "best_candidate_id": result["best_id"],
            "best_candidate_score": result["best_score"],
        })
        print(f"{row['ref']}: {result['status']}" + (f" ({result['reason']})" if result["reason"] else ""), flush=True)
        time.sleep(0.15)
    with gzip.open(out / f"{name}.jsonl.gz", "wt", encoding="utf-8") as f:
        for work in records:
            f.write(json.dumps(work, ensure_ascii=False) + "\n")
    with (out / f"{name}_matches.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ref", "status", "openalex_id", "score", "best_candidate_id", "best_candidate_score"])
        writer.writeheader()
        writer.writerows(matches)
    summary = {
        "mode": "titles", "rows": len(rows), "found": len(records), "not_found": len(rows) - len(records),
        "title_threshold": TITLE_THRESHOLD, "year_window": 1,
        "refetched_for_full_authorships": refetched,
        "not_found_reasons": reasons,
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (out / f"{name}_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "not_found_reasons"}, indent=2))


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
    parser.add_argument("ids_file", type=Path, nargs="?")
    parser.add_argument("--titles", type=Path, help="CSV with ref,title,year,first_author")
    parser.add_argument("--out", type=Path, default=Path("lookup_out"))
    args = parser.parse_args()
    if args.titles:
        run_titles(args.titles, args.out)
        return
    if not args.ids_file:
        parser.error("give an ids_file or --titles")

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
