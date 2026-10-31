# MUHAS Publications Observatory

A pilot, OpenAlex-based record of MUHAS publications. It is reported by MUHAS fiscal year (1 July to 30 June) and fiscal quarter (Q1 Jul–Sep, Q2 Oct–Dec, Q3 Jan–Mar, Q4 Apr–Jun), refreshed after each quarter closes and cleaned progressively.

Institutional anchor:

- OpenAlex: `I154840374`
- ROR: `027pr6c67`
- Alternate name: Chuo Kikuu cha Afya na Sayansi Shirikishi Muhimbili

## Snapshots

`scripts/build_muhas_observatory.py`, run by `.github/workflows/build-muhas-observatory.yml`, harvests OpenAlex on schedule. Each final snapshot is archived unchanged as a GitHub Release tagged `muhas-pubs-<as_of>-final`, containing:

- the raw OpenAlex records (`.jsonl.gz`), which are the citable source of record;
- the works and authorships CSVs, the SQLite database and the full Excel workbook;
- the manifest, including `changes_since_previous`, the comparison with the previous final snapshot;
- the **quarterly report** (`<snapshot>_quarterly_report.xlsx`), which lists works published in the quarter and works added to OpenAlex in the quarter but published earlier.

## Definitions

- **Published in a quarter:** the publication date falls in that fiscal quarter.
- **Added in a quarter:** OpenAlex created the record in that quarter. OpenAlex re-created most existing records on 10 October 2025, so "added" counts are shown only for quarters starting after that date.
- **Flagged repository deposits:** repository-hosted records (PubMed exempt) added to OpenAlex in 2026 or later, with a publication date at least three years earlier. They are counted in the totals and can be excluded on the page.

## Internal author report

`scripts/quarterly_author_report.py` turns a release's works and authorships CSVs into a per-author workbook for one quarter. For each MUHAS-affiliated author it counts works, first-author works and corresponding-author works. The output is for DRPI only: it is not published, and authors are listed by name, not ranked.

## Schools and departments

School and department fields remain unassigned until MUHAS approves a time-aware affiliation crosswalk. The staff directory is owned by the OSP project.
