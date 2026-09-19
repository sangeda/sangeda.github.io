#!/usr/bin/env python3
"""Build an ORCID-seeded publication catalogue and research-trend visuals.

Sources: ORCID Public API, Crossref REST API, and NCBI PubMed E-utilities.
Only ORCID-linked records are queried to reduce author-name ambiguity.
"""

from __future__ import annotations

import html
import json
import math
import random
import re
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORCID = "0000-0002-6574-5308"
USER_AGENT = "sangeda-publications-site/1.0"
CURRENT_YEAR = datetime.now(timezone.utc).year


def fetch(url: str, accept: str = "application/json", attempts: int = 3) -> bytes:
    request = urllib.request.Request(
        url, headers={"Accept": accept, "User-Agent": USER_AGENT}
    )
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def clean_text(value: str | None) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def normalize_doi(value: str | None) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value)
    return value.rstrip(" .")


def normalize_title(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", clean_text(value)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def year_from_date_parts(parts) -> int | None:
    try:
        year = int(parts[0][0])
        return year if 1950 <= year <= CURRENT_YEAR + 1 else None
    except (TypeError, ValueError, IndexError):
        return None


def from_crossref() -> list[dict]:
    query = urllib.parse.urlencode({"filter": f"orcid:{ORCID}", "rows": 1000})
    payload = json.loads(fetch(f"https://api.crossref.org/works?{query}"))
    records = []
    for item in payload.get("message", {}).get("items", []):
        authors = []
        for author in item.get("author", []):
            name = " ".join(x for x in [author.get("given"), author.get("family")] if x)
            if name:
                authors.append(name)
        date = item.get("published-print") or item.get("published-online") or item.get("issued") or {}
        doi = normalize_doi(item.get("DOI"))
        records.append({
            "title": clean_text((item.get("title") or [""])[0]),
            "year": year_from_date_parts(date.get("date-parts")),
            "journal": clean_text((item.get("container-title") or [""])[0]),
            "doi": doi,
            "pmid": "",
            "url": f"https://doi.org/{doi}" if doi else item.get("URL", ""),
            "authors": authors,
            "type": item.get("type", ""),
            "sources": ["Crossref"],
        })
    return records


def from_orcid() -> list[dict]:
    payload = json.loads(fetch(f"https://pub.orcid.org/v3.0/{ORCID}/works"))
    records = []
    for group in payload.get("group", []):
        summaries = group.get("work-summary", [])
        if not summaries:
            continue
        item = summaries[0]
        title = (((item.get("title") or {}).get("title") or {}).get("value")) or ""
        year = ((item.get("publication-date") or {}).get("year") or {}).get("value")
        external = {}
        for ext in (item.get("external-ids") or {}).get("external-id", []):
            external[ext.get("external-id-type", "").lower()] = ext.get("external-id-value", "")
        doi = normalize_doi(external.get("doi"))
        records.append({
            "title": clean_text(title),
            "year": int(year) if year and str(year).isdigit() else None,
            "journal": clean_text((item.get("journal-title") or {}).get("value")),
            "doi": doi,
            "pmid": str(external.get("pmid", "")),
            "url": f"https://doi.org/{doi}" if doi else (item.get("url") or {}).get("value", ""),
            "authors": [],
            "type": item.get("type", ""),
            "sources": ["ORCID"],
        })
    return records


def from_pubmed() -> list[dict]:
    term = urllib.parse.quote(f"{ORCID}[Author Identifier]")
    search = json.loads(fetch(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        f"?db=pubmed&term={term}&retmax=500&retmode=json"
    ))
    ids = search.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    xml_bytes = fetch(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        f"?db=pubmed&id={','.join(ids)}&retmode=xml",
        accept="application/xml",
    )
    root = ET.fromstring(xml_bytes)
    records = []
    for article in root.findall(".//PubmedArticle"):
        citation = article.find("MedlineCitation")
        journal_article = citation.find("Article") if citation is not None else None
        if journal_article is None:
            continue
        title_node = journal_article.find("ArticleTitle")
        title = "".join(title_node.itertext()) if title_node is not None else ""
        journal = journal_article.findtext("Journal/Title", "")
        pmid = citation.findtext("PMID", "")
        doi = ""
        for identifier in article.findall("PubmedData/ArticleIdList/ArticleId"):
            if identifier.attrib.get("IdType") == "doi":
                doi = normalize_doi(identifier.text)
        year_text = (
            journal_article.findtext("Journal/JournalIssue/PubDate/Year")
            or journal_article.findtext("ArticleDate/Year")
            or ""
        )
        if not year_text:
            medline_date = journal_article.findtext("Journal/JournalIssue/PubDate/MedlineDate", "")
            match = re.search(r"(?:19|20)\d{2}", medline_date)
            year_text = match.group(0) if match else ""
        authors = []
        for author in journal_article.findall("AuthorList/Author"):
            name = " ".join(x for x in [author.findtext("ForeName"), author.findtext("LastName")] if x)
            if name:
                authors.append(name)
        records.append({
            "title": clean_text(title),
            "year": int(year_text) if year_text.isdigit() else None,
            "journal": clean_text(journal),
            "doi": doi,
            "pmid": pmid,
            "url": f"https://doi.org/{doi}" if doi else f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "authors": authors,
            "type": "journal-article",
            "sources": ["PubMed"],
        })
    return records


def merge_records(records: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    title_keys: dict[str, str] = {}
    for item in records:
        if not item.get("title"):
            continue
        doi = normalize_doi(item.get("doi"))
        title_key = normalize_title(item.get("title"))
        key = f"doi:{doi}" if doi else title_keys.get(title_key, f"title:{title_key}")
        if key not in merged:
            merged[key] = item.copy()
            merged[key]["doi"] = doi
        else:
            current = merged[key]
            for field in ("title", "year", "journal", "doi", "pmid", "url", "type"):
                if not current.get(field) and item.get(field):
                    current[field] = item[field]
            if len(item.get("authors", [])) > len(current.get("authors", [])):
                current["authors"] = item["authors"]
            current["sources"] = sorted(set(current.get("sources", []) + item.get("sources", [])))
        title_keys[title_key] = key
    return sorted(
        merged.values(), key=lambda x: (x.get("year") or 0, x.get("title", "")), reverse=True
    )


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "among", "associated", "based", "between",
    "by", "case", "clinical", "cohort", "comparison", "cross", "dar", "data", "during",
    "effects", "evaluation", "evidence", "for", "from", "health", "in", "including",
    "into", "is", "management", "national", "of", "on", "outcomes", "patients", "people",
    "prevalence", "research", "retrospective", "review", "risk", "sectional", "study",
    "sub", "systematic", "tanzania", "tanzanian", "the", "their", "to", "towards", "trends",
    "using", "with", "within", "years", "east", "africa", "african", "analysis", "assessment",
    "salaam", "patterns", "factors", "hospital", "living", "patients", "adults", "children",
    "findings", "experience", "approach", "care", "selected", "role", "impact", "utilization",
    "muhimbili", "tertiary", "nigeria", "district", "regional", "sites", "facility", "facilities",
}

PHRASES = [
    "hiv drug resistance", "antimicrobial resistance", "antibiotic consumption",
    "sickle cell disease", "sickle cell", "health systems", "bioinformatics capacity",
    "genomic medicine", "next generation sequencing", "implementation fidelity",
    "essential medicines", "quality of life", "drug resistance", "antiretroviral therapy",
    "supply chain", "fetal haemoglobin", "public health", "machine learning",
]

THEMES = {
    "HIV and treatment": ["hiv", "antiretroviral", "viral suppression", "drug resistance"],
    "AMR and antibiotic use": ["antimicrobial", "antibiotic", "stewardship", "resistance"],
    "Sickle cell and genomics": ["sickle", "haemoglobin", "hemoglobin", "genomic", "genetic", "pharmacogen"],
    "Medicines and supply systems": ["medicine", "pharmaceutical", "quantification", "supply chain", "drug quality"],
    "Health systems and implementation": ["health system", "implementation", "retention", "service", "redcap"],
    "Infections and microbiology": ["infection", "bacteria", "microbi", "malaria", "tuberculosis", "covid"],
}


def topic_counts(publications: list[dict]) -> tuple[Counter, dict]:
    terms = Counter()
    trend = defaultdict(Counter)
    for item in publications:
        title = item["title"].lower().replace("-", " ")
        year = item.get("year")
        phrase_spans = title
        for phrase in sorted(PHRASES, key=len, reverse=True):
            count = phrase_spans.count(phrase)
            if count:
                terms[phrase] += count * 2
                phrase_spans = phrase_spans.replace(phrase, " ")
        for token in re.findall(r"[a-z][a-z0-9]+", phrase_spans):
            if len(token) >= 4 and token not in STOPWORDS:
                terms[token] += 1
        if year:
            for theme, needles in THEMES.items():
                if any(needle in title for needle in needles):
                    trend[year][theme] += 1
    return terms, trend


def write_wordcloud_svg(terms: Counter, path: Path) -> None:
    selected = [(term, count) for term, count in terms.most_common(55) if count >= 2]
    width, height = 1400, 760
    random.seed(42)
    placed = []
    colors = ["#0f716c", "#07514e", "#3f6e99", "#c96852", "#a97819", "#365d59"]
    max_count = max((count for _, count in selected), default=1)
    elements = []
    for index, (term, count) in enumerate(selected):
        size = 14 + 34 * math.sqrt(count / max_count)
        box_w = max(40, len(term) * size * 0.56)
        box_h = size * 1.2
        found = None
        for step in range(900):
            angle = step * 0.34 + index
            radius = 10 * math.sqrt(step)
            x = width / 2 + radius * math.cos(angle) - box_w / 2
            y = height / 2 + radius * math.sin(angle) - box_h / 2
            if x < 15 or y < 15 or x + box_w > width - 15 or y + box_h > height - 15:
                continue
            if not any(x < px + pw and x + box_w > px and y < py + ph and y + box_h > py for px, py, pw, ph in placed):
                found = (x, y)
                break
        if found:
            x, y = found
            placed.append((x, y, box_w, box_h))
            elements.append(
                f'<text x="{x + box_w/2:.1f}" y="{y + size:.1f}" text-anchor="middle" '
                f'font-size="{size:.1f}" font-weight="700" fill="{colors[index % len(colors)]}">'
                f'{html.escape(term)}</text>'
            )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" '
        f'aria-labelledby="title desc"><title id="title">Publication title word cloud</title>'
        f'<desc id="desc">Prominent terms across ORCID-linked publication titles.</desc>'
        f'<rect width="100%" height="100%" rx="28" fill="#f5f7f2"/>'
        f'<g font-family="Arial, sans-serif">{"".join(elements)}</g></svg>'
    )
    path.write_text(svg, encoding="utf-8")


def write_trends_svg(trend: dict, path: Path) -> dict:
    years = sorted(y for y in trend if CURRENT_YEAR - 9 <= y <= CURRENT_YEAR)
    totals = Counter()
    for year in years:
        totals.update(trend[year])
    themes = [theme for theme, _ in totals.most_common(6)]
    width, height = 1200, 560
    left, top, right, bottom = 250, 55, 45, 75
    plot_w, plot_h = width - left - right, height - top - bottom
    max_value = max((trend[y][t] for y in years for t in themes), default=1)
    colors = ["#0f716c", "#d7a33d", "#3f6e99", "#c96852", "#745e9b", "#63864b"]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
             '<title id="title">Research themes by publication year</title>',
             '<desc id="desc">Annual counts of ORCID-linked publications grouped by title keywords. Papers can appear in more than one theme.</desc>',
             '<rect width="100%" height="100%" rx="28" fill="#f5f7f2"/>']
    for tick in range(max_value + 1):
        y = top + plot_h - (tick / max_value) * plot_h
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#d9e0dc"/>')
        parts.append(f'<text x="{left-14}" y="{y+5:.1f}" text-anchor="end" font-size="13" fill="#657373">{tick}</text>')
    for idx, year in enumerate(years):
        x = left + idx * (plot_w / max(1, len(years)-1))
        parts.append(f'<text x="{x:.1f}" y="{height-34}" text-anchor="middle" font-size="13" fill="#657373">{year}</text>')
    for theme_i, theme in enumerate(themes):
        points = []
        for idx, year in enumerate(years):
            x = left + idx * (plot_w / max(1, len(years)-1))
            y = top + plot_h - (trend[year][theme] / max_value) * plot_h
            points.append((x, y, trend[year][theme]))
        color = colors[theme_i]
        parts.append('<polyline fill="none" stroke="{}" stroke-width="4" points="{}"/>'.format(color, " ".join(f"{x:.1f},{y:.1f}" for x,y,_ in points)))
        for x, y, value in points:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}"><title>{html.escape(theme)}: {value}</title></circle>')
        legend_y = 48 + theme_i * 34
        parts.append(f'<line x1="22" y1="{legend_y}" x2="48" y2="{legend_y}" stroke="{color}" stroke-width="5"/>')
        parts.append(f'<text x="58" y="{legend_y+5}" font-size="14" fill="#172427">{html.escape(theme)}</text>')
    parts.append('</svg>')
    path.write_text("".join(parts), encoding="utf-8")
    return {"years": years, "themes": themes, "counts": {str(y): dict(trend[y]) for y in years}}


def publication_card(item: dict) -> str:
    authors = item.get("authors", [])
    author_text = ", ".join(authors[:6])
    if len(authors) > 6:
        author_text += ", et al."
    badges = "".join(f"<span>{html.escape(source)}</span>" for source in item.get("sources", []))
    link = item.get("url") or (f"https://doi.org/{item['doi']}" if item.get("doi") else "")
    title = html.escape(item["title"])
    title_html = f'<a href="{html.escape(link)}">{title}</a>' if link else title
    return f'''<article class="pub-card" data-year="{item.get('year') or ''}" data-search="{html.escape((item['title'] + ' ' + item.get('journal','')).lower())}">
      <div class="pub-year">{item.get('year') or '—'}</div>
      <div><h3>{title_html}</h3><p class="pub-authors">{html.escape(author_text)}</p>
      <p class="pub-journal">{html.escape(item.get('journal') or 'Source not supplied')}</p><div class="source-badges">{badges}</div></div>
    </article>'''


def write_publications_page(publications: list[dict], terms: Counter, trends: dict, timestamp: str) -> None:
    years = [p["year"] for p in publications if p.get("year")]
    recent = sum(1 for year in years if year >= CURRENT_YEAR - 4)
    top_terms = terms.most_common(12)
    cards = "\n".join(publication_card(item) for item in publications)
    option_years = "".join(f'<option value="{year}">{year}</option>' for year in sorted(set(years), reverse=True))
    ranked = "".join(f'<li><span>{html.escape(term)}</span><strong>{count}</strong></li>' for term, count in top_terms)
    page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="ORCID-linked publications and research trends for Prof. Raphael Z. Sangeda.">
<title>Publications &amp; research trends | Raphael Z. Sangeda</title><link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&amp;family=Manrope:wght@500;600;700;800&amp;display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/style.css"></head><body>
<header class="site-header"><div class="nav-wrap"><a class="brand" href="index.html"><span class="brand-mark">RZS</span><span>Raphael Z. Sangeda</span></a>
<nav class="site-nav always"><a href="index.html">Home</a><a href="#trends">Trends</a><a href="#catalogue">Catalogue</a><a class="nav-cta" href="https://orcid.org/{ORCID}">ORCID</a></nav></div></header>
<main><section class="pub-hero"><p class="eyebrow">Public scholarship</p><h1>Publications &amp; <span>research trends.</span></h1>
<p class="hero-lead">A reproducible catalogue assembled from records linked to ORCID across ORCID, Crossref and PubMed. Updated {html.escape(timestamp)}.</p>
<div class="hero-stats"><div><strong>{len(publications)}</strong><span>unique indexed records</span></div><div><strong>{recent}</strong><span>published in the latest five years</span></div><div><strong>{min(years) if years else '—'}–{max(years) if years else '—'}</strong><span>publication-year span</span></div></div></section>
<section id="trends" class="section tinted"><div class="section-heading"><div><p class="section-kicker">Research signature</p><h2>What the publication titles emphasize</h2></div><p>Term prominence and thematic patterns are calculated from titles. They describe this indexed subset, not citation impact.</p></div>
<div class="visual-card"><img src="assets/publication_wordcloud.svg" alt="Word cloud of prominent publication-title terms"></div>
<div class="trend-grid"><div class="visual-card"><img src="assets/publication_trends.svg" alt="Line chart of research-theme publication counts by year"></div>
<aside class="ranked-terms"><h3>Most frequent terms</h3><ol>{ranked}</ol></aside></div>
<p class="method-note">Theme counts use transparent title-keyword rules; a paper may contribute to more than one theme. Word size reflects title frequency, not scientific importance or citation impact.</p></section>
<section id="catalogue" class="section"><div class="section-heading"><div><p class="section-kicker">Catalogue</p><h2>Browse the indexed works</h2></div><p>For the authoritative researcher-managed record, consult ORCID.</p></div>
<div class="pub-controls"><label>Search<input id="pub-search" type="search" placeholder="Title or journal"></label><label>Year<select id="pub-year"><option value="">All years</option>{option_years}</select></label><span id="pub-count">{len(publications)} records</span></div>
<div id="publication-list" class="publication-catalogue">{cards}</div></section></main>
<footer><p>© {CURRENT_YEAR} Raphael Z. Sangeda</p><p>Automated from public scholarly metadata · <a href="data/publications.json">Download JSON</a></p></footer>
<script src="assets/publications.js"></script></body></html>'''
    (ROOT / "publications.html").write_text(page, encoding="utf-8")


def main() -> None:
    fetched = []
    source_counts = {}
    for name, loader in (("ORCID", from_orcid), ("Crossref", from_crossref), ("PubMed", from_pubmed)):
        items = loader()
        source_counts[name] = len(items)
        fetched.extend(items)
    publications = merge_records(fetched)
    terms, trend = topic_counts(publications)
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "assets").mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%d %B %Y")
    write_wordcloud_svg(terms, ROOT / "assets/publication_wordcloud.svg")
    trend_payload = write_trends_svg(trend, ROOT / "assets/publication_trends.svg")
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "orcid": ORCID,
        "scope_note": "Records linked to the ORCID iD in ORCID, Crossref, or PubMed; not a definitive bibliography.",
        "source_record_counts_before_deduplication": source_counts,
        "unique_record_count": len(publications),
        "top_title_terms": [{"term": term, "count": count} for term, count in terms.most_common(50)],
        "topic_trends": trend_payload,
        "publications": publications,
    }
    (ROOT / "data/publications.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_publications_page(publications, terms, trend_payload, timestamp)
    print(json.dumps({"sources": source_counts, "unique": len(publications), "years": trend_payload["years"]}))


if __name__ == "__main__":
    main()
    from build_site_seo import optimise_site
    optimise_site()

