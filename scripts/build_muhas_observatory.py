#!/usr/bin/env python3
"""Build the MUHAS Publications Observatory from OpenAlex.

The raw API snapshot is immutable. Derived tables add reporting-period fields
and are regenerated from raw data. Department/school assignment is deliberately
left for a versioned institutional crosswalk rather than inferred from names.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import html
import json
import shutil
import sqlite3
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "muhas-publications"
DOWNLOADS = SITE / "downloads"
DATA = SITE / "data"
RAW = ROOT / "muhas_publications_archive" / "raw"

INSTITUTION_NAME = "Muhimbili University of Health and Allied Sciences"
INSTITUTION_ALT_NAME = "Chuo Kikuu cha Afya na Sayansi Shirikishi Muhimbili"
OPENALEX_ID = "I154840374"
ROR = "027pr6c67"
START_DATE = date(1964, 1, 1)
USER_AGENT = "muhas-publications-observatory/1.0"

WORK_FIELDS = [
    "id", "doi", "title", "display_name", "publication_year", "publication_date",
    "type", "language", "cited_by_count", "fwci", "is_retracted", "is_paratext",
    "is_xpac", "countries_distinct_count", "institutions_distinct_count", "authorships",
    "primary_location", "open_access", "primary_topic", "topics", "keywords",
    "sustainable_development_goals", "corresponding_author_ids",
    "corresponding_institution_ids", "created_date", "updated_date",
]


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def short_id(value: str | None) -> str:
    return (value or "").rstrip("/").rsplit("/", 1)[-1]


def fiscal_period(d: date) -> tuple[str, str, date]:
    if 7 <= d.month <= 9:
        start, quarter, end = d.year, "Q1", date(d.year, 9, 30)
    elif 10 <= d.month <= 12:
        start, quarter, end = d.year, "Q2", date(d.year, 12, 31)
    elif 1 <= d.month <= 3:
        start, quarter, end = d.year - 1, "Q3", date(d.year, 3, 31)
    else:
        start, quarter, end = d.year - 1, "Q4", date(d.year, 6, 30)
    return f"FY{start}/{str(start + 1)[-2:]}", quarter, end


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


def fetch_openalex(as_of: date, raw_path: Path) -> tuple[list[dict], dict]:
    works: list[dict] = []
    cursor = "*"
    page = 0
    filter_value = (
        f"authorships.institutions.lineage:{OPENALEX_ID},"
        f"from_publication_date:{START_DATE.isoformat()},"
        f"to_publication_date:{as_of.isoformat()}"
    )
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(raw_path, "wt", encoding="utf-8") as stream:
        while cursor:
            query = urllib.parse.urlencode({
                "filter": filter_value,
                "select": ",".join(WORK_FIELDS),
                "per-page": 200,
                "cursor": cursor,
            })
            payload = api_json(f"https://api.openalex.org/works?{query}")
            page += 1
            batch = payload.get("results", [])
            for work in batch:
                stream.write(json.dumps(work, ensure_ascii=False) + "\n")
            works.extend(batch)
            cursor = payload.get("meta", {}).get("next_cursor")
            if not batch:
                break
            print(f"OpenAlex page {page}: {len(works):,} works", flush=True)
            time.sleep(0.12)
    return works, {
        "query_filter": filter_value,
        "openalex_reported_count": len(works),
        "pages_retrieved": page,
        "raw_path": str(raw_path.relative_to(ROOT)),
    }


def join_names(items: list[dict] | None, field: str = "display_name") -> str:
    return " | ".join(str(item.get(field, "")).strip() for item in (items or []) if item.get(field))


def process_works(works: list[dict], retrieved_at: str, snapshot_id: str) -> tuple[list[dict], list[dict]]:
    work_rows: list[dict] = []
    author_rows: list[dict] = []
    for work in works:
        try:
            published = date.fromisoformat(work.get("publication_date") or f"{work['publication_year']}-01-01")
        except Exception:
            continue
        fy, quarter, period_end = fiscal_period(published)
        authorships = work.get("authorships") or []
        muhas_authors = []
        countries = set()
        corresponding_names = []
        corresponding_ids = set(work.get("corresponding_author_ids") or [])
        for authorship in authorships:
            author = authorship.get("author") or {}
            institutions = authorship.get("institutions") or []
            has_muhas = any(OPENALEX_ID in (inst.get("lineage") or []) or short_id(inst.get("id")) == OPENALEX_ID for inst in institutions)
            name = author.get("display_name") or ""
            if has_muhas and name:
                muhas_authors.append(name)
            if author.get("id") in corresponding_ids and name:
                corresponding_names.append(name)
            countries.update(authorship.get("countries") or [])
            author_rows.append({
                "snapshot_id": snapshot_id,
                "openalex_work_id": short_id(work.get("id")),
                "doi": (work.get("doi") or "").replace("https://doi.org/", ""),
                "publication_date": published.isoformat(),
                "fiscal_year": fy,
                "fiscal_quarter": quarter,
                "author_id": short_id(author.get("id")),
                "orcid": (author.get("orcid") or "").replace("https://orcid.org/", ""),
                "author_name": name,
                "author_position": authorship.get("author_position") or "",
                "is_corresponding": bool(authorship.get("is_corresponding")),
                "has_muhas_affiliation": has_muhas,
                "institution_ids": " | ".join(short_id(x.get("id")) for x in institutions if x.get("id")),
                "institution_names": join_names(institutions),
                "institution_rors": " | ".join((x.get("ror") or "").replace("https://ror.org/", "") for x in institutions if x.get("ror")),
                "countries": " | ".join(sorted(authorship.get("countries") or [])),
                "school": "",
                "department": "",
                "curation_status": "unreviewed",
                "retrieved_at": retrieved_at,
            })
        primary_location = work.get("primary_location") or {}
        source = primary_location.get("source") or {}
        open_access = work.get("open_access") or {}
        primary_topic = work.get("primary_topic") or {}
        topics = work.get("topics") or []
        keywords = work.get("keywords") or []
        sdgs = work.get("sustainable_development_goals") or []
        corresponding_institutions = set(work.get("corresponding_institution_ids") or [])
        work_rows.append({
            "snapshot_id": snapshot_id,
            "openalex_work_id": short_id(work.get("id")),
            "doi": (work.get("doi") or "").replace("https://doi.org/", ""),
            "title": work.get("title") or work.get("display_name") or "",
            "publication_date": published.isoformat(),
            "publication_year": published.year,
            "fiscal_year": fy,
            "fiscal_quarter": quarter,
            "period_end": period_end.isoformat(),
            "work_type": work.get("type") or "",
            "language": work.get("language") or "",
            "journal_or_source": source.get("display_name") or "",
            "source_openalex_id": short_id(source.get("id")),
            "issn_l": source.get("issn_l") or "",
            "publisher": source.get("host_organization_name") or "",
            "open_access_status": open_access.get("oa_status") or "",
            "is_open_access": bool(open_access.get("is_oa")),
            "open_access_url": open_access.get("oa_url") or "",
            "cited_by_count_at_snapshot": work.get("cited_by_count") or 0,
            "fwci_at_snapshot": work.get("fwci"),
            "is_retracted": bool(work.get("is_retracted")),
            "is_paratext": bool(work.get("is_paratext")),
            "is_xpac": bool(work.get("is_xpac")),
            "authors_count": len(authorships),
            "muhas_authors_count": len(muhas_authors),
            "muhas_authors": " | ".join(muhas_authors),
            "corresponding_authors": " | ".join(corresponding_names),
            "has_muhas_corresponding_institution": any(short_id(x) == OPENALEX_ID for x in corresponding_institutions),
            "countries": " | ".join(sorted(countries)),
            "countries_count": work.get("countries_distinct_count") or len(countries),
            "institutions_count": work.get("institutions_distinct_count") or 0,
            "international_collaboration": len(countries) > 1,
            "primary_topic": primary_topic.get("display_name") or "",
            "primary_subfield": (primary_topic.get("subfield") or {}).get("display_name") or "",
            "primary_field": (primary_topic.get("field") or {}).get("display_name") or "",
            "primary_domain": (primary_topic.get("domain") or {}).get("display_name") or "",
            "topics": join_names(topics),
            "keywords": join_names(keywords),
            "sustainable_development_goals": join_names(sdgs),
            "openalex_created_date": work.get("created_date") or "",
            "openalex_updated_date": work.get("updated_date") or "",
            "retrieved_at": retrieved_at,
            "school": "",
            "department": "",
            "curation_status": "unreviewed",
        })
    return work_rows, author_rows


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def summaries(work_rows: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    annual = Counter(row["publication_year"] for row in work_rows)
    quarterly = Counter((row["fiscal_year"], row["fiscal_quarter"], row["period_end"]) for row in work_rows)
    types = Counter(row["work_type"] or "unknown" for row in work_rows)
    annual_rows = [{"publication_year": year, "publications": count} for year, count in sorted(annual.items())]
    quarter_rows = [
        {"fiscal_year": fy, "fiscal_quarter": q, "period_end": end, "publications": count}
        for (fy, q, end), count in sorted(quarterly.items())
    ]
    type_rows = [{"work_type": kind, "publications": count} for kind, count in types.most_common()]
    return annual_rows, quarter_rows, type_rows


def write_sqlite(path: Path, works: list[dict], authorships: list[dict], manifest: dict) -> None:
    if path.exists():
        path.unlink()
    journal_path = Path(str(path) + "-journal")
    if journal_path.exists():
        journal_path.unlink()
    connection = sqlite3.connect(path)
    try:
        # A self-contained downloadable database must not depend on a rollback
        # journal that can be separated from it during copying or download.
        connection.execute("PRAGMA journal_mode=OFF")
        connection.execute("PRAGMA synchronous=OFF")
        for table, rows in (("works", works), ("authorships", authorships)):
            columns = list(rows[0])
            connection.execute(f'CREATE TABLE {table} ({", ".join(f"[{c}] TEXT" for c in columns)})')
            connection.executemany(
                f'INSERT INTO {table} VALUES ({", ".join("?" for _ in columns)})',
                [[str(row.get(col, "")) if row.get(col) is not None else "" for col in columns] for row in rows],
            )
        connection.execute("CREATE TABLE snapshots (snapshot_id TEXT, metadata_json TEXT)")
        connection.execute("INSERT INTO snapshots VALUES (?, ?)", (manifest["snapshot_id"], json.dumps(manifest)))
        connection.execute("CREATE INDEX idx_works_date ON works(publication_date)")
        connection.execute("CREATE INDEX idx_auth_work ON authorships(openalex_work_id)")
        connection.execute("CREATE INDEX idx_auth_author ON authorships(author_id)")
        connection.commit()
        result = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {result}")
        if connection.execute("SELECT COUNT(*) FROM works").fetchone()[0] != len(works):
            raise RuntimeError("SQLite works row count does not match source rows")
    finally:
        connection.close()


def style_sheet(ws) -> None:
    fill = PatternFill("solid", fgColor="0F716C")
    for cell in ws[1]:
        cell.fill = fill
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for column in range(1, min(ws.max_column, 40) + 1):
        values = [str(ws.cell(row=r, column=column).value or "") for r in range(1, min(ws.max_row, 200) + 1)]
        ws.column_dimensions[get_column_letter(column)].width = min(45, max(10, max(map(len, values), default=10) + 2))


def append_rows(ws, rows: list[dict]) -> None:
    if not rows:
        return
    ws.append(list(rows[0]))
    for row in rows:
        ws.append([row.get(column, "") for column in rows[0]])
    style_sheet(ws)


def write_excel(path: Path, works: list[dict], authorships: list[dict], annual: list[dict], quarters: list[dict], types: list[dict], manifest: dict) -> None:
    wb = Workbook(write_only=False)
    summary = wb.active
    summary.title = "Executive_Summary"
    summary.append(["MUHAS Publications Observatory", "Value"])
    summary_rows = [
        ("Institution", INSTITUTION_NAME), ("Alternate name", INSTITUTION_ALT_NAME),
        ("ROR", ROR), ("OpenAlex ID", OPENALEX_ID), ("Snapshot ID", manifest["snapshot_id"]),
        ("Retrieved at", manifest["retrieved_at"]), ("Period through", manifest["as_of_date"]),
        ("Works", len(works)), ("Authorship rows", len(authorships)),
        ("Important", "OpenAlex-derived inception dataset; school and department assignments require institutional curation."),
    ]
    for row in summary_rows:
        summary.append(row)
    style_sheet(summary)
    for name, rows in (
        ("Publications", works), ("Authorships", authorships), ("Annual_Summary", annual),
        ("Quarterly_Summary", quarters), ("Type_Summary", types),
        ("Snapshot_Metadata", [{"field": k, "value": json.dumps(v) if isinstance(v, (dict, list)) else v} for k, v in manifest.items()]),
    ):
        append_rows(wb.create_sheet(name), rows)
    curation = wb.create_sheet("Affiliation_Crosswalk")
    append_rows(curation, [{
        "author_id": "", "orcid": "", "author_name": "", "school": "", "department": "",
        "effective_from": "", "effective_to": "", "curation_status": "", "evidence": "",
        "curated_by": "", "curated_at": "",
    }])
    dictionary = wb.create_sheet("Data_Dictionary")
    append_rows(dictionary, [
        {"field": "period_end", "definition": "Official end date of the MUHAS fiscal quarter containing the publication date."},
        {"field": "retrieved_at", "definition": "Actual UTC timestamp when the source API data were retrieved."},
        {"field": "snapshot_id", "definition": "Immutable identifier for the extraction run."},
        {"field": "curation_status", "definition": "Institutional review status; inception records default to unreviewed."},
        {"field": "cited_by_count_at_snapshot", "definition": "OpenAlex citation count at retrieval; not publication productivity."},
        {"field": "school / department", "definition": "Blank until assigned through the versioned MUHAS affiliation crosswalk."},
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def build_dashboard(work_rows: list[dict], annual: list[dict], quarter_rows: list[dict], type_rows: list[dict], manifest: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    summary = {
        "institution": INSTITUTION_NAME,
        "openalex_id": OPENALEX_ID,
        "ror": ROR,
        "snapshot": manifest,
        "total_works": len(work_rows),
        "historical_1964_2025": sum(row["publication_year"] <= 2025 for row in work_rows),
        "annual": annual,
        "quarters": quarter_rows,
        "types": type_rows[:15],
        "open_access": dict(Counter(row["open_access_status"] or "unknown" for row in work_rows)),
        "top_topics": [
            {"topic": topic, "publications": count}
            for topic, count in Counter(row["primary_topic"] for row in work_rows if row["primary_topic"]).most_common(25)
        ],
    }
    (DATA / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MUHAS Publications Observatory</title><meta name="description" content="Reproducible OpenAlex-based MUHAS publication reporting by year and fiscal quarter.">
<link rel="stylesheet" href="../assets/style.css"><link rel="icon" href="../assets/favicon.svg" type="image/svg+xml"></head><body>
<header class="site-header"><div class="nav-wrap"><a class="brand" href="../index.html"><span class="brand-mark">MU</span><span>MUHAS Publications Observatory</span></a><nav class="site-nav always"><a href="../index.html">Profile</a><a href="#downloads">Downloads</a><a href="#methods">Methods</a></nav></div></header>
<main><section class="pub-hero"><p class="eyebrow">Institutional research intelligence</p><h1>MUHAS publications, <span>preserved and reportable.</span></h1>
<p class="hero-lead">An OpenAlex-based inception database designed for annual, fiscal-quarter, school and department reporting. Organisational assignments will be added through controlled institutional curation.</p>
<div class="hero-stats"><div><strong>{len(work_rows):,}</strong><span>works through {manifest['as_of_date']}</span></div><div><strong>{sum(row['publication_year'] <= 2025 for row in work_rows):,}</strong><span>historical works, 1964–2025</span></div><div><strong>{manifest['snapshot_status'].title()}</strong><span>snapshot status</span></div><div><strong>{html.escape(manifest['retrieved_at'][:10])}</strong><span>retrieval date</span></div></div></section>
<section class="section tinted"><div class="section-heading"><div><p class="section-kicker">Reporting</p><h2>Annual and fiscal-quarter views</h2></div><p>Publication dates determine reporting periods. Retrieval timestamps independently document when the evidence was downloaded.</p></div><div id="muhas-summary" class="observatory-grid"></div></section>
<section id="downloads" class="section"><div class="section-heading"><div><p class="section-kicker">Downloads</p><h2>Current inception dataset</h2></div><p>Excel is formatted for institutional review; CSV supports analysis in R, Python, Power BI and other systems.</p></div>
<div class="download-grid"><a href="downloads/MUHAS_Publications_LATEST.xlsx"><strong>Excel workbook</strong><span>Publications, authorships, summaries, metadata and curation template</span></a><a href="downloads/MUHAS_Publications_LATEST.csv"><strong>Publications CSV</strong><span>One row per OpenAlex work</span></a><a href="downloads/MUHAS_Authorships_LATEST.csv"><strong>Authorships CSV</strong><span>One row per author–publication relationship</span></a><a href="downloads/MUHAS_Publications_LATEST.sqlite"><strong>SQLite database</strong><span>Works, authorships and snapshot metadata</span></a></div></section>
<section id="methods" class="section dark"><div class="section-heading"><div><p class="section-kicker">Methods and cautions</p><h2>Broad at inception; curated thereafter.</h2></div></div><div class="prose"><p>The extraction uses OpenAlex institution lineage <code>{OPENALEX_ID}</code> and ROR <code>{ROR}</code>. Records are retained broadly at inception. School and department fields remain blank until MUHAS validates a time-aware author affiliation crosswalk.</p><p>OpenAlex records can be incomplete, delayed or incorrectly affiliated. Counts are therefore provisional research-intelligence evidence, not an audited institutional return, until curation is completed.</p></div></section></main>
<footer><p>MUHAS Publications Observatory · Inception implementation</p><p>Snapshot {html.escape(manifest['snapshot_id'])}</p></footer><script src="assets/observatory.js"></script></body></html>'''
    (SITE / "index.html").write_text(page, encoding="utf-8")


def build_js() -> None:
    assets = SITE / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    script = '''fetch("data/summary.json").then(r=>r.json()).then(d=>{const years=d.annual.filter(x=>x.publication_year>=2016);const recent=years.slice(-10);const max=Math.max(...recent.map(x=>x.publications),1);const annual=recent.map(x=>`<div class="mini-bar-row"><span>${x.publication_year}</span><i style="width:${100*x.publications/max}%"></i><strong>${x.publications}</strong></div>`).join("");const qs=d.quarters.slice(-8).reverse().map(x=>`<tr><td>${x.fiscal_year}</td><td>${x.fiscal_quarter}</td><td>${x.period_end}</td><td>${x.publications}</td></tr>`).join("");const topics=d.top_topics.slice(0,10).map(x=>`<li><span>${x.topic}</span><strong>${x.publications}</strong></li>`).join("");document.querySelector("#muhas-summary").innerHTML=`<article class="observatory-card"><h3>Recent annual output</h3><div class="mini-bars">${annual}</div></article><article class="observatory-card"><h3>Latest fiscal quarters</h3><table><thead><tr><th>FY</th><th>Quarter</th><th>Ends</th><th>Works</th></tr></thead><tbody>${qs}</tbody></table></article><article class="observatory-card"><h3>Leading OpenAlex topics</h3><ol class="topic-rank">${topics}</ol></article>`;}).catch(()=>{document.querySelector("#muhas-summary").textContent="Summary data are temporarily unavailable.";});'''
    (assets / "observatory.js").write_text(script, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", default=date.today().isoformat())
    parser.add_argument("--status", choices=["provisional", "final"], default="provisional")
    parser.add_argument("--reuse-raw", type=Path)
    args = parser.parse_args()
    as_of = date.fromisoformat(args.as_of)
    retrieved_at = iso_now()
    snapshot_id = f"MUHAS_OPENALEX_{START_DATE.year}_{as_of.isoformat()}_{args.status.upper()}_asof_{retrieved_at[:10]}"
    raw_path = RAW / f"{snapshot_id}.jsonl.gz"
    if args.reuse_raw:
        works = [json.loads(line) for line in gzip.open(args.reuse_raw, "rt", encoding="utf-8")]
        query_meta = {"query_filter": "reused raw snapshot", "openalex_reported_count": len(works), "pages_retrieved": None, "raw_path": str(args.reuse_raw)}
    else:
        works, query_meta = fetch_openalex(as_of, raw_path)
    work_rows, author_rows = process_works(works, retrieved_at, snapshot_id)
    annual_rows, quarter_rows, type_rows = summaries(work_rows)
    manifest = {
        "snapshot_id": snapshot_id,
        "snapshot_status": args.status,
        "institution_name": INSTITUTION_NAME,
        "alternate_name": INSTITUTION_ALT_NAME,
        "openalex_id": OPENALEX_ID,
        "ror": ROR,
        "period_start": START_DATE.isoformat(),
        "as_of_date": as_of.isoformat(),
        "retrieved_at": retrieved_at,
        "works_processed": len(work_rows),
        "authorship_rows": len(author_rows),
        **query_meta,
    }
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    dated_csv = DOWNLOADS / f"{snapshot_id}_works.csv"
    dated_auth = DOWNLOADS / f"{snapshot_id}_authorships.csv"
    dated_db = DOWNLOADS / f"{snapshot_id}.sqlite"
    dated_xlsx = DOWNLOADS / f"{snapshot_id}.xlsx"
    write_csv(dated_csv, work_rows)
    write_csv(dated_auth, author_rows)
    write_sqlite(dated_db, work_rows, author_rows, manifest)
    write_excel(dated_xlsx, work_rows, author_rows, annual_rows, quarter_rows, type_rows, manifest)
    for source, stable in (
        (dated_csv, DOWNLOADS / "MUHAS_Publications_LATEST.csv"),
        (dated_auth, DOWNLOADS / "MUHAS_Authorships_LATEST.csv"),
        (dated_db, DOWNLOADS / "MUHAS_Publications_LATEST.sqlite"),
        (dated_xlsx, DOWNLOADS / "MUHAS_Publications_LATEST.xlsx"),
    ):
        shutil.copy2(source, stable)
    (DATA / "snapshot_manifest.json").parent.mkdir(parents=True, exist_ok=True)
    (DATA / "snapshot_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    build_dashboard(work_rows, annual_rows, quarter_rows, type_rows, manifest)
    build_js()
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
