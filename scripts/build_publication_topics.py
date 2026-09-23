#!/usr/bin/env python3
"""Build normalized publication-topic data from the current publication catalogue.

This is a derived, non-visible data layer. It does not modify publication titles,
the existing static word cloud, or the public publications page.
"""
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLICATIONS = ROOT / "data" / "publications.json"
CONCEPTS = ROOT / "scripts" / "research_concepts.json"
OUTPUT = ROOT / "data" / "publication_topics.json"


def norm(value):
    value = unicodedata.normalize("NFKC", str(value or "")).casefold().replace("’", "'")
    value = value.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", value).strip()


def concept_matches(text, concepts):
    matches = set()
    for canonical, aliases in concepts.items():
        for alias in sorted(aliases, key=len, reverse=True):
            a = norm(alias)
            if re.search(r"(?<![a-z0-9])" + re.escape(a) + r"(?![a-z0-9])", text):
                matches.add(canonical)
                break
    return sorted(matches)


def main():
    payload = json.loads(PUBLICATIONS.read_text(encoding="utf-8"))
    publications = payload["publications"]
    concepts = json.loads(CONCEPTS.read_text(encoding="utf-8"))

    counts = Counter()
    by_topic = defaultdict(list)
    records = []

    for i, pub in enumerate(publications, start=1):
        title = pub.get("title", "")
        topics = concept_matches(norm(title), concepts)
        for topic in topics:
            counts[topic] += 1
            by_topic[topic].append(i)
        records.append({
            "id": i,
            "title": title,
            "year": pub.get("year"),
            "doi": pub.get("doi", ""),
            "topics": topics,
        })

    out = {
        "schema_version": 1,
        "source": "data/publications.json titles",
        "source_updated_at": payload.get("generated_at", payload.get("updated_at", "")),
        "publication_count": len(publications),
        "concept_count": len(concepts),
        "matched_publications": sum(1 for r in records if r["topics"]),
        "topic_counts": [
            {"topic": topic, "publications": count}
            for topic, count in sorted(counts.items(), key=lambda x: (-x[1], x[0]))
        ],
        "topics": {
            topic: {"publications": counts[topic], "record_ids": by_topic[topic]}
            for topic in sorted(by_topic)
        },
        "records": records,
    }
    OUTPUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Normalized publication topics: {out['matched_publications']}/"
        f"{out['publication_count']} publications matched {len(counts)} concepts."
    )


if __name__ == "__main__":
    main()
