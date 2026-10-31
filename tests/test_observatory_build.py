"""Offline tests for the Observatory builder: no network, no API key needed."""

import io
import os
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_muhas_observatory as obs  # noqa: E402

MUHAS = {"id": f"https://openalex.org/{obs.OPENALEX_ID}", "lineage": [f"https://openalex.org/{obs.OPENALEX_ID}"]}
OTHER = {"id": "https://openalex.org/I1", "lineage": ["https://openalex.org/I1"]}


def authorship(n: int, muhas: bool) -> dict:
    return {
        "author": {"id": f"https://openalex.org/A{n}", "display_name": f"Author {n}"},
        "author_position": "middle",
        "institutions": [MUHAS if muhas else OTHER],
        "countries": ["TZ" if muhas else "GB"],
    }


def work(n_authors: int, muhas_positions=(), work_id="W1", truncated=None) -> dict:
    record = {
        "id": f"https://openalex.org/{work_id}",
        "ids": {"pmid": "https://pubmed.ncbi.nlm.nih.gov/12345", "pmcid": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC999"},
        "publication_date": "2025-08-15",
        "publication_year": 2025,
        "authorships": [authorship(i, i in muhas_positions) for i in range(1, n_authors + 1)],
    }
    if truncated is not None:
        record["is_authors_truncated"] = truncated
    return record


class AuthorsDisplayTests(unittest.TestCase):
    def test_short_list_is_complete(self):
        names = [f"A{i}" for i in range(1, 101)]
        self.assertEqual(obs.authors_display(names, [False] * 100), " | ".join(names))

    def test_long_list_keeps_99_then_muhas_with_position_then_total(self):
        names = [f"A{i}" for i in range(1, 2781)]
        flags = [i in (5, 1412, 2780) for i in range(1, 2781)]
        text = obs.authors_display(names, flags)
        parts = text.split(" | ")
        self.assertEqual(parts[:99], names[:99])
        self.assertIn("[MUHAS] A1412 (pos. 1,412)", parts)
        self.assertIn("[MUHAS] A2780 (pos. 2,780)", parts)
        self.assertNotIn("[MUHAS] A5 (pos. 5)", parts)  # already shown among the first 99
        self.assertEqual(parts[-1], "… (2,780 authors)")
        self.assertEqual(len(parts), 99 + 2 + 1)


class ApiKeyTests(unittest.TestCase):
    def test_key_appended_and_redacted(self):
        with mock.patch.dict(os.environ, {"OPENALEX_API_KEY": "secret123"}):
            url = obs.with_api_key("https://api.openalex.org/works?filter=x")
        self.assertTrue(url.endswith("&api_key=secret123"))
        self.assertNotIn("secret123", obs.redact(url))

    def test_no_key_leaves_url_unchanged(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(obs.with_api_key("https://api.openalex.org/works/W1"), "https://api.openalex.org/works/W1")

    def test_401_fails_at_once_without_leaking_key(self):
        error = urllib.error.HTTPError("u", 401, "Unauthorized", {}, io.BytesIO(b""))
        with mock.patch.dict(os.environ, {"OPENALEX_API_KEY": "secret123"}), \
                mock.patch.object(obs.urllib.request, "urlopen", side_effect=error) as urlopen, \
                mock.patch.object(obs.time, "sleep"):
            with self.assertRaises(obs.OpenAlexAuthError) as caught:
                obs.api_json("https://api.openalex.org/works?filter=x")
        self.assertEqual(urlopen.call_count, 1)
        self.assertNotIn("secret123", str(caught.exception))


class CompleteAuthorshipsTests(unittest.TestCase):
    def test_capped_works_are_refetched_others_untouched(self):
        capped = work(100, muhas_positions=(), work_id="W1")
        flagged = work(40, muhas_positions=(1,), work_id="W2", truncated=True)
        normal = work(12, muhas_positions=(1,), work_id="W3")
        full = {"W1": work(250, muhas_positions=(180,), work_id="W1"), "W2": work(40, muhas_positions=(1,), work_id="W2")}
        calls = []

        def fake(url):
            calls.append(url)
            return full[url.split("/works/")[1].split("?")[0]]

        works = [capped, flagged, normal]
        with mock.patch.object(obs, "api_json", side_effect=fake), mock.patch.object(obs.time, "sleep"):
            self.assertEqual(obs.complete_authorships(works), 2)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(works[0]["authorships"]), 250)
        self.assertTrue(works[0]["list_authors_truncated"])
        self.assertIs(works[2], normal)

    def test_shorter_full_record_is_an_error(self):
        works = [work(100, work_id="W1")]
        with mock.patch.object(obs, "api_json", return_value=work(80, work_id="W1")), mock.patch.object(obs.time, "sleep"):
            with self.assertRaises(RuntimeError):
                obs.complete_authorships(works)


class ProcessWorksTests(unittest.TestCase):
    def test_muhas_author_beyond_100_is_attributed_and_shown(self):
        record = work(250, muhas_positions=(180,))
        record["list_authors_truncated"] = True
        work_rows, author_rows = obs.process_works([record], "2026-10-31T00:00:00+00:00", "TEST")
        row = work_rows[0]
        self.assertEqual(len(author_rows), 250)
        self.assertEqual(row["muhas_authors_count"], 1)
        self.assertIn("[MUHAS] Author 180 (pos. 180)", row["authors"])
        self.assertTrue(row["list_authors_truncated"])
        self.assertEqual((row["pmid"], row["pmcid"]), ("12345", "PMC999"))
        muhas_rows = [r for r in author_rows if r["has_muhas_affiliation"]]
        self.assertEqual([r["author_sequence"] for r in muhas_rows], [180])


class FetchDedupTests(unittest.TestCase):
    def test_duplicate_records_from_paging_are_dropped(self):
        pages = [
            {"results": [work(3, work_id="W1"), work(3, work_id="W2")], "meta": {"next_cursor": "c2"}},
            {"results": [work(3, work_id="W2"), work(3, work_id="W3")], "meta": {"next_cursor": "c3"}},
            {"results": [], "meta": {"next_cursor": None}},
        ]
        import tempfile, gzip, json
        from datetime import date
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(obs, "ROOT", Path(tmp)), \
                mock.patch.object(obs, "api_json", side_effect=pages), \
                mock.patch.object(obs.time, "sleep"):
            raw = Path(tmp) / "raw" / "x.jsonl.gz"
            works, meta = obs.fetch_openalex(date(2026, 10, 31), raw)
            with gzip.open(raw, "rt") as f:
                lines = f.readlines()
        self.assertEqual([obs.short_id(w["id"]) for w in works], ["W1", "W2", "W3"])
        self.assertEqual(len(lines), 3)
        self.assertEqual(meta["duplicate_records_dropped"], 1)


class SnapshotChangesTests(unittest.TestCase):
    def test_compare_counts_and_neutral_note(self):
        old = {w: work(3, muhas_positions=(1,), work_id=w) for w in ("W1", "W2", "W3")}
        deposit = work(3, muhas_positions=(1,), work_id="W3")
        deposit.update({"created_date": "2026-03-01", "publication_year": 2019,
                        "primary_location": {"source": {"type": "repository", "display_name": "Zenodo"}}})
        old["W3"] = deposit
        current = [old["W1"], work(3, muhas_positions=(1,), work_id="W4")]
        report = obs.compare_works(old, current, query_api=False)
        self.assertEqual((report["added"], report["removed"], report["removed_matching_backdated_rule"]), (1, 2, 1))
        note = obs.changes_html({"previous_snapshot": "muhas-pubs-2026-09-30-final", **report,
                                 "removed_status_now": {"not_returned_deleted_or_merged": 2}})
        self.assertIn("Changes since the 2026-09-30 snapshot.", note)
        self.assertIn("1 works were added and 2 are no longer included.", note)
        self.assertIn("archived unchanged", note)
        self.assertEqual(obs.changes_html(None), "")


class FiscalReportingTests(unittest.TestCase):
    @staticmethod
    def row(pub, created, flagged=False, topic="T"):
        fy, q, end = obs.fiscal_period(obs.date.fromisoformat(pub))
        return {"publication_date": pub, "fiscal_year": fy, "fiscal_quarter": q, "period_end": end.isoformat(),
                "openalex_created_date": created, "flag_backdated_repository_deposit": flagged,
                "primary_topic": topic, "title": pub, "publication_year": int(pub[:4])}

    def test_quarters_fiscal_years_and_added(self):
        rows = [
            self.row("2026-10-05", "2026-10-20"),            # Q2 FY2026/27, added Q2
            self.row("2026-06-30", "2026-11-02"),            # Q4 FY2025/26, added Q2 (late)
            self.row("2019-01-01", "2026-12-01", True),      # flagged deposit added Q2
            self.row("2025-07-01", "2025-10-10", topic="X"), # FY2025/26, rebuild date
        ]
        r = obs.reporting_metrics(rows, obs.date(2026, 12, 31))
        latest = r["latest_quarter"]
        self.assertEqual((latest["fiscal_year"], latest["fiscal_quarter"], latest["partial"]), ("FY2026/27", "Q2", False))
        self.assertEqual((latest["published"], latest["added"], latest["added_excluding_flagged"]), (1, 3, 2))
        self.assertEqual(latest["added_published_earlier"], 2)
        self.assertEqual(r["works_before_current_fiscal_year"], 3)
        self.assertEqual(r["topics_fiscal_year"], "FY2025/26")
        by_q = {(q["fiscal_year"], q["fiscal_quarter"]): q for q in r["quarters"]}
        self.assertIsNone(by_q[("FY2025/26", "Q2")]["added"])      # spans the 10 Oct 2025 rebuild
        self.assertEqual(by_q[("FY2025/26", "Q3")]["added"], 0)     # first reliable quarter
        self.assertTrue(r["fiscal_years"][-1]["partial"])

    def test_partial_quarter_and_report(self):
        rows = [self.row("2026-10-05", "2026-10-20"), self.row("2026-01-01", "2026-10-25")]
        r = obs.reporting_metrics(rows, obs.date(2026, 10, 31))
        self.assertTrue(r["latest_quarter"]["partial"])
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            counts = obs.write_quarterly_report(Path(d) / "q.xlsx", rows, {
                "as_of_date": "2026-10-31", "snapshot_status": "provisional", "snapshot_id": "X"})
        self.assertEqual(counts["quarter"], "FY2026/27 Q2 (to date)")
        self.assertEqual((counts["published_in_quarter"], counts["added_in_quarter_published_earlier"]), (1, 1))


if __name__ == "__main__":
    unittest.main()
