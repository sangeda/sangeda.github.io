#!/usr/bin/env python3
"""Internal per-author quarterly workbook for DRPI. Not published on the site.

Reads a snapshot's works and authorships CSVs (from its GitHub Release) and
counts, for each MUHAS-affiliated author, the works published in one MUHAS
fiscal quarter: all works, as first author and as corresponding author.
Authors are listed by name, not ranked. School and department stay blank until
the staff affiliation crosswalk is approved.

  python scripts/quarterly_author_report.py --works X_works.csv \
      --authorships X_authorships.csv --quarter FY2026/27-Q2 --out authors.xlsx
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_muhas_observatory as obs  # noqa: E402


def read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def author_rows(works: list[dict], authorships: list[dict], fiscal_year: str, quarter: str) -> list[dict]:
    in_quarter = {w["openalex_work_id"] for w in works if (w["fiscal_year"], w["fiscal_quarter"]) == (fiscal_year, quarter)}
    people: dict[str, dict] = {}
    works_by_author: dict[str, set] = defaultdict(set)
    first: dict[str, set] = defaultdict(set)
    corresponding: dict[str, set] = defaultdict(set)
    for a in authorships:
        if a["openalex_work_id"] not in in_quarter or not obs.truthy(a.get("has_muhas_affiliation")) or not a.get("author_id"):
            continue
        key = a["author_id"]
        people.setdefault(key, {"author_id": key, "author_name": a.get("author_name", ""), "orcid": a.get("orcid", "")})
        works_by_author[key].add(a["openalex_work_id"])
        if str(a.get("author_sequence", "")) == "1" or a.get("author_position") == "first":
            first[key].add(a["openalex_work_id"])
        if obs.truthy(a.get("is_corresponding")):
            corresponding[key].add(a["openalex_work_id"])
    rows = [
        {**p, "works_in_quarter": len(works_by_author[k]), "as_first_author": len(first[k]),
         "as_corresponding_author": len(corresponding[k]), "school": "", "department": ""}
        for k, p in people.items()
    ]
    return sorted(rows, key=lambda r: (r["author_name"].split()[-1:] or [""], r["author_name"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--works", type=Path, required=True)
    parser.add_argument("--authorships", type=Path, required=True)
    parser.add_argument("--quarter", required=True, help="e.g. FY2026/27-Q2")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    fiscal_year, quarter = args.quarter.rsplit("-", 1)
    rows = author_rows(read(args.works), read(args.authorships), fiscal_year, quarter)
    wb = Workbook()
    readme = wb.active
    readme.title = "Read_me"
    for item in [
        ("MUHAS Publications Observatory: authors, internal", ""),
        ("Quarter", f"{fiscal_year} {quarter}"),
        ("Source", f"{args.works.name}; {args.authorships.name}"),
        ("Use", "Internal to DRPI. Not for publication or ranking; authors are listed by name."),
        ("Counts", "Works published in the quarter with a MUHAS affiliation for this author; first-author and corresponding-author counts are subsets."),
        ("Caveats", "OpenAlex author profiles can be split (one person, several IDs) or merged; counts are pilot data, cleaned progressively. "
                    "Schools and departments await the approved staff affiliation crosswalk."),
        ("Authors", len(rows)),
    ]:
        readme.append(list(item))
    obs.style_sheet(readme)
    readme.column_dimensions["A"].width = 24
    readme.column_dimensions["B"].width = 110
    ws = wb.create_sheet("Authors_quarter")
    if rows:
        obs.append_rows(ws, rows)
    else:
        ws.append(["No MUHAS-affiliated authors in this quarter."])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(args.out)
    print(f"{len(rows)} authors -> {args.out}")


if __name__ == "__main__":
    main()
