#!/usr/bin/env python3
"""Read-only health check for MUHAS REDCap Project 224.

Uses only the API token from the environment. Never exports names, project
titles, registration numbers, student records, or API credentials to logs.
No write or import action exists in this script.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

API_URL = "https://utafiti.muhas.ac.tz/api/"
PROJECT_ID = "224"
REQUIRED_FIELDS = frozenset({
    "record_id", "student_name", "regno", "completion_year", "title",
    "source_refs", "report_status", "curation_status", "public_catalogue",
    "public_author", "public_abstract", "public_report", "curation_notes",
})
CANDIDATE_IDS = frozenset(f"BPH{number:06d}" for number in range(802, 1141))
ID_PATTERN = re.compile(r"BPH(\d{6})\Z")


class PreflightError(Exception):
    pass


def request(token, content, **options):
    if not token:
        raise PreflightError("GitHub secret REDCAP_PROJECT224_TOKEN is unavailable.")
    params = dict(token=token, content=content, format="json",
                  returnFormat="json", **options)
    body = urllib.parse.urlencode(params).encode("utf-8")
    try:
        req = urllib.request.Request(API_URL, data=body, method="POST")
        with urllib.request.urlopen(req, timeout=90) as response:
            result = json.load(response)
    except Exception as exc:
        # Do not print remote bodies or request objects; they might contain data.
        raise PreflightError("REDCap API request or JSON decoding failed.") from None
    if isinstance(result, dict) and ("error" in result or "errors" in result):
        raise PreflightError("REDCap API returned an error.")
    return result


def evaluate(client):
    project = client("project")
    if not isinstance(project, dict) or str(project.get("project_id", "")) != PROJECT_ID:
        raise PreflightError("Connected REDCap API token is not for Project 224.")
    metadata = client("metadata")
    if not isinstance(metadata, list):
        raise PreflightError("Live metadata response is not a list.")
    live_fields = {str(item.get("field_name", "")) for item in metadata
                   if isinstance(item, dict)}
    missing = sorted(REQUIRED_FIELDS - live_fields)
    if missing:
        # Field names are schema, not personally identifying.
        raise PreflightError("Live Project 224 is missing required fields: " + ", ".join(missing))
    records = client("record", action="export", type="flat", rawOrLabel="raw",
                     **{"fields[0]": "record_id"})
    if not isinstance(records, list):
        raise PreflightError("Live record ID export is not a list.")
    record_ids = []
    for item in records:
        if not isinstance(item, dict):
            raise PreflightError("Malformed record ID response.")
        rid = str(item.get("record_id", "")).strip()
        if not rid:
            raise PreflightError("Blank record ID in live response.")
        record_ids.append(rid)
    if len(set(record_ids)) != len(record_ids):
        raise PreflightError("Duplicate record IDs returned by live Project 224.")
    colliding = CANDIDATE_IDS.intersection(record_ids)
    numeric_ids = [int(match.group(1)) for rid in record_ids
                   if (match := ID_PATTERN.fullmatch(rid))]
    return {
        "project_id_verified": True,
        "required_fields_verified": len(REQUIRED_FIELDS),
        "live_record_count": len(record_ids),
        "highest_bph_numeric_record_id": max(numeric_ids, default=None),
        "proposed_new_record_count": len(CANDIDATE_IDS),
        "proposed_id_range": "BPH000802-BPH001140",
        "proposed_id_collisions": len(colliding),
        "id_range_available": not bool(colliding),
        "note": ("Read-only check. No import was performed. Live ID availability "
                 "must be checked again immediately before each write batch."),
    }


def main():
    token = os.environ.get("REDCAP_PROJECT224_TOKEN", "")
    if not token:
        raise PreflightError("GitHub secret REDCAP_PROJECT224_TOKEN is unavailable.")
    def client(content, **options):
        return request(token, content, **options)
    print(json.dumps(evaluate(client), indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PreflightError as exc:
        print(f"READ-ONLY PREFLIGHT STOPPED: {exc}", file=sys.stderr)
        sys.exit(2)
