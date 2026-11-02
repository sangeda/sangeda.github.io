#!/usr/bin/env python3
"""Version-5-approved BPharm supervisor normalization: live compare-and-update.

The repository contains only mappings of academic supervisor names and a SHA-256
digest of the *private* approved 249-field change set. It does NOT contain
student rows, IDs paired with supervisors, or an API token.

Operations: preflight (read-only), first_five, remaining. Write operations
require explicit confirmations and full live-state validation.
"""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request

API_URL = "https://utafiti.muhas.ac.tz/api/"
FIELDS = ["record_id"] + [f"supervisor_{i}" for i in range(1, 5)]
ALIASES = json.loads(
    (Path(__file__).resolve().with_name("project224_supervisor_verified_aliases.json"))
    .read_text(encoding="utf-8")
)
EXPECTED_ALL_SHA = "854500d8f293cd1a9b38adf097f3bdb68398b16181b88cee3306b04a9404e397"
EXPECTED_REMAINING_SHA = "45192cd664606f680d0bbcc0d6b16a7fe8efcd4cc0bad31a8e6a1df6f9be0141"
EXPECTED_LEGACY_CHANGES = 249
EXPECTED_AFFECTED_RECORDS = 239
FIRST_FIVE = tuple(f"BPH{i:06d}" for i in range(1, 6))
FIRST_FIVE_OLD = ("NGASSAPA", "NGASSAPA", "NGASSAPA", "DR.NGASSAPA", "NGASSAPA")
FIRST_FIVE_NEW = ("Olipa Ngassapa",) * 5
CONFIRMATIONS = {
    "first_five": "NORMALIZE PROJECT 224 FIRST FIVE",
    "remaining": "NORMALIZE PROJECT 224 REMAINING",
}

class Stop(Exception):
    pass

def api(token, content, **options):
    if not token:
        raise Stop("REDCAP_PROJECT224_TOKEN GitHub secret is missing.")
    body = urllib.parse.urlencode(dict(
        token=token, content=content, format="json", returnFormat="json",
        **options,
    )).encode("utf-8")
    try:
        request = urllib.request.Request(API_URL, data=body, method="POST")
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.load(response)
    except Exception:
        # Deliberately avoid echoing HTTP bodies, request fields or credentials.
        raise Stop("A REDCap API request failed. Check the server and permissions privately.") from None
    if isinstance(result, dict) and ("error" in result or "errors" in result):
        raise Stop("REDCap rejected a request; no automatic retries.")
    return result

def read_live(client):
    project = client("project")
    if not isinstance(project, dict) or str(project.get("project_id")) != "224":
        raise Stop("This API token is not for Project 224.")
    metadata = client("metadata")
    names = {r.get("field_name") for r in metadata if isinstance(r, dict)} if isinstance(metadata, list) else set()
    if not set(FIELDS).issubset(names):
        raise Stop("Project 224 dictionary no longer matches the approved supervisor fields.")
    raw = client(
        "record", action="export", type="flat", rawOrLabel="raw",
        **{f"fields[{i}]": f for i, f in enumerate(FIELDS)}
    )
    if not isinstance(raw, list):
        raise Stop("Unexpected record export format.")
    records = {}
    for row in raw:
        if not isinstance(row, dict):
            raise Stop("Unexpected record entry.")
        key = str(row.get("record_id", ""))
        if not key or key in records:
            raise Stop("Missing or repeated live record ID.")
        records[key] = {name: str(row.get(name, "") or "") for name in FIELDS}
    if len(records) != 1114:
        raise Stop("Live record count differs from verified 1,114-record baseline.")
    if any(rid not in records for rid in FIRST_FIVE):
        raise Stop("One of the five test IDs is missing.")
    return records

def change_plan(records, exclude_first_five=False):
    plan = []
    for rid, row in records.items():
        match = re.fullmatch(r"BPH(\d{6})", rid)
        if not match or int(match.group(1)) > 801:
            continue
        if exclude_first_five and rid in FIRST_FIVE:
            continue
        for i in range(1, 5):
            field = f"supervisor_{i}"
            old = row[field]
            new = ALIASES.get(old)
            if new is not None and old != new:
                plan.append((rid, i, old, new))
    return sorted(plan)

def fingerprint(plan):
    lines = [f"{rid}\t{i}\t{old}\t{new}\n" for rid,i,old,new in plan]
    return hashlib.sha256("".join(sorted(lines)).encode("utf-8")).hexdigest()

def verify_first(records, updated):
    for rid, old, new in zip(FIRST_FIVE, FIRST_FIVE_OLD, FIRST_FIVE_NEW):
        observed = records[rid]["supervisor_1"]
        expected = new if updated else old
        if observed != expected:
            raise Stop("The first-five supervisor values differ from the approved snapshot.")

def validate_plan(records, phase):
    if phase in ("preflight", "first_five"):
        verify_first(records, updated=False)
        plan = change_plan(records)
        if (len(plan) != EXPECTED_LEGACY_CHANGES
                or len({x[0] for x in plan}) != EXPECTED_AFFECTED_RECORDS
                or fingerprint(plan) != EXPECTED_ALL_SHA):
            raise Stop("Live supervisor changes differ from the approved 249-field baseline.")
        counts = collections.Counter(i for _,i,_,_ in plan)
        if [counts[i] for i in range(1,5)] != [218,21,8,2]:
            raise Stop("Live changes do not match the approved supervisor-field distribution.")
    elif phase == "remaining":
        verify_first(records, updated=True)
        plan = change_plan(records, exclude_first_five=True)
        if (len(plan) != 244 or len({x[0] for x in plan}) != 234
                or fingerprint(plan) != EXPECTED_REMAINING_SHA):
            raise Stop("Remaining supervisor changes differ from the approved baseline.")
    else:
        raise Stop("Unknown phase.")
    return plan

def make_updates(plan):
    grouped = {}
    for rid,i,old,new in plan:
        if rid not in grouped:
            grouped[rid] = {"record_id": rid}
        grouped[rid][f"supervisor_{i}"] = new
    return [grouped[rid] for rid in sorted(grouped)]

def apply_batch(client, live, batch):
    # Compare all four supervisor fields before import to prevent stale edits.
    current = read_live(client)
    for update in batch:
        rid = update["record_id"]
        if current.get(rid) != live.get(rid):
            raise Stop("Live record changed since preflight; no further writes.")
    result = client(
        "record", action="import", type="flat", overwriteBehavior="normal",
        forceAutoNumber="false", returnContent="count",
        data=json.dumps(batch, ensure_ascii=False),
    )
    if not isinstance(result, dict) or str(result.get("count")) != str(len(batch)):
        raise Stop("Unexpected import count; stop and inspect before retry.")
    after = read_live(client)
    for update in batch:
        rid = update["record_id"]
        wanted = dict(current[rid])
        wanted.update(update)
        if after.get(rid) != wanted:
            raise Stop("Supervisor readback mismatch; stop without retrying.")
        live[rid] = wanted
    return len(batch)

def execute(client, operation, confirmation):
    if operation not in ("preflight", "first_five", "remaining"):
        raise Stop("Invalid operation.")
    if operation != "preflight" and confirmation != CONFIRMATIONS[operation]:
        raise Stop("Exact write confirmation missing; no API writes attempted.")
    live = read_live(client)
    plan = validate_plan(live, operation)
    report = {
        "operation": operation,
        "project_id_verified": True,
        "live_records_verified": len(live),
        "approved_changes_remaining": len(plan),
        "affected_records_remaining": len({x[0] for x in plan}),
        "approved_snapshot_fingerprint_verified": True,
        "records_written": 0,
        "field_values_changed": 0,
    }
    if operation == "preflight":
        report["ready_for_first_five"] = True
        return report
    if operation == "first_five":
        selected = [x for x in plan if x[0] in FIRST_FIVE]
        if len(selected) != 5 or [x[0] for x in selected] != list(FIRST_FIVE):
            raise Stop("The first-five sample is not the approved five changes.")
        batch = make_updates(selected)
        count = apply_batch(client, live, batch)
        verify_first(live, updated=True)
        report.update(records_written=count, field_values_changed=len(selected), readback_verified=True)
        return report
    grouped = make_updates(plan)
    updated = 0
    for start in range(0, len(grouped), 20):
        batch = grouped[start:start+20]
        updated += apply_batch(client, live, batch)
    report.update(records_written=updated, field_values_changed=len(plan), readback_verified=True)
    return report

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--operation", choices=("preflight", "first_five", "remaining"), default="preflight")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    token = os.getenv("REDCAP_PROJECT224_TOKEN", "")
    def client(content, **options):
        return api(token, content, **options)
    print(json.dumps(execute(client, args.operation, args.confirm), indent=2))

if __name__ == "__main__":
    try:
        main()
    except Stop as exc:
        print(f"PROJECT 224 SUPERVISOR SAFETY STOP: {exc}", file=sys.stderr)
        sys.exit(2)
