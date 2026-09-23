"""Rebuild derived search indexes from a current REDCap flat JSON export.

Usage: python bpharm_indexes.py INPUT.json OUTPUT_DIR [--public-only]
No external packages, network requests or source-data writes.
"""
import argparse
import collections
import json
import re
import unicodedata
from pathlib import Path

ALIAS_PATH = Path(__file__).with_name("bpharm_supervisor_aliases.json")
SUPERVISOR_ALIASES = (
    json.loads(ALIAS_PATH.read_text(encoding="utf-8"))
    if ALIAS_PATH.exists()
    else {}
)

STOP = set(
    "a an and are as at be been being by for from in into is it its of on or "
    "that the their these this to using used use with among between study "
    "assessment evaluation analysis investigation prevalence knowledge "
    "practice practices".split()
)

PHRASES = [
    "antimicrobial resistance",
    "antibiotic resistance",
    "medication adherence",
    "adverse drug reactions",
    "medicinal plants",
    "community pharmacies",
    "drug interactions",
    "quality of life",
    "antimicrobial activity",
    "antiretroviral therapy",
    "sickle cell",
    "diabetes mellitus",
    "public health",
    "supply chain",
]


def normalized(s):
    return unicodedata.normalize("NFKC", str(s)).casefold().replace("’", "'")


def terms(title, curated=""):
    t = normalized(title)
    words = set(re.findall(r"[a-z][a-z0-9]*(?:[-'][a-z0-9]+)*", t))
    result = {w for w in words if len(w) > 2 and w not in STOP}
    result.update(
        p for p in PHRASES
        if re.search(r"(?<!\w)" + re.escape(p) + r"(?!\w)", t)
    )
    result.update(
        normalized(k).strip()
        for k in re.split(r"[;\n]", curated or "")
        if k.strip()
    )
    return sorted(result)


def supervisor_identity(label):
    raw = unicodedata.normalize("NFKC", str(label or "")).replace("’", "'").strip()
    raw = re.sub(r"([a-z])([A-Z])", r"\1 \2", raw)
    raw = re.sub(r"\s*\((?:sop|itm|muhas)\)\s*$", "", raw, flags=re.I)
    raw = re.sub(
        r"^(?:(?:prof(?:essor)?|dr|mr|mrs|ms|pharm)\.?\s*)+",
        "",
        raw,
        flags=re.I,
    ).strip(" .,-")
    key = raw.casefold()
    key = re.sub(r"[^a-z0-9' -]+", " ", key)
    key = re.sub(r"\s+", " ", key).strip()
    return key, raw


def canonical_supervisor(label):
    key, raw = supervisor_identity(label)
    if key in SUPERVISOR_ALIASES:
        name = SUPERVISOR_ALIASES[key]
        canonical_key, _ = supervisor_identity(name)
        return name, canonical_key
    if raw and (raw.isupper() or raw.islower()):
        raw = raw.title()
    return raw, key


def supervisors(record):
    result = []
    seen = set()
    for i in range(1, 5):
        value = str(record.get(f"supervisor_{i}", "") or "")
        for label in re.split(r"\s+and\s+|[;\n]", value, flags=re.I):
            name, key = canonical_supervisor(label)
            if (
                key
                and not key.isdigit()
                and key != "unnamed supervisor"
                and key not in seen
            ):
                seen.add(key)
                result.append({"name": name, "search_key": key})
    return result


def yes(v):
    return str(v).strip().lower() in {"1", "yes", "true"}


def main():
    a = argparse.ArgumentParser()
    a.add_argument("input")
    a.add_argument("output")
    a.add_argument("--public-only", action="store_true")
    args = a.parse_args()

    records = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    if not isinstance(records, list):
        raise ValueError("Expected an array of flat REDCap records")

    ids = [r.get("record_id") for r in records]
    if any(not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError(
            "Expected one unique record_id per project; resolve repeating rows first"
        )

    projects = []
    counts = collections.Counter()
    supervisor_index = collections.defaultdict(set)

    for r in records:
        if args.public_only and (
            not yes(r.get("public_catalogue"))
            or str(r.get("curation_status")) in {"1", "3"}
        ):
            continue

        keyword = terms(r.get("title", "") or "", r.get("keywords", "") or "")
        sups = supervisors(r)
        counts.update(keyword)

        for s in sups:
            supervisor_index[s["search_key"]].add(r["record_id"])

        p = {
            k: r.get(k, "")
            for k in [
                "record_id",
                "title",
                "completion_year",
                "department",
                "subject_area",
            ]
        }
        if not args.public_only or yes(r.get("public_author")):
            p["student_name"] = r.get("student_name", "")
        p.update(search_terms=keyword, supervisors=sups)
        projects.append(p)

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    outputs = {
        "projects.json": projects,
        "term_counts.json": [
            {"term": k, "projects": v}
            for k, v in sorted(counts.items(), key=lambda x: (-x[1], x[0]))
        ],
        "supervisors.json": [
            {"search_key": k, "project_ids": sorted(v)}
            for k, v in sorted(supervisor_index.items())
        ],
    }

    for name, value in outputs.items():
        (out / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(f"Indexed {len(projects)} projects; public-only={args.public_only}")


if __name__ == "__main__":
    main()
