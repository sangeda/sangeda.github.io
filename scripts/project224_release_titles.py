#!/usr/bin/env python3
"""One-time, explicitly authorized title-only release for REDCap Project 224.

Approval: user confirmed on 2026-11-03 that 334 nonblank project titles may be
public, WITHOUT student authors or registration numbers. The five blank-title
records remain private and every record retains its existing curation status.
No private student data is printed, cached or committed to GitHub.
"""
import collections
import json
import os
import re
import sys
import urllib.parse
import urllib.request

API_URL = "https://utafiti.muhas.ac.tz/api/"
TOKEN_ENV = "REDCAP_PROJECT224_TOKEN"
APPROVAL = "RELEASE PROJECT 224 TITLES ONLY 334"
FIELDS = ("record_id", "title", "completion_year", "source_refs",
          "curation_status", "public_catalogue", "public_author",
          "public_abstract", "public_report")
EXPECTED_YEARS = {"2020":37, "2021":51, "2022":28, "2023":47,
                  "2024":56, "2025":51, "2026":69}
NEW_IDS = {f"BPH{n:06d}" for n in range(802,1141)}

class Stop(Exception):
    pass

def api(token, content, **options):
    if not token:
        raise Stop("REDCAP_PROJECT224_TOKEN is missing.")
    body = urllib.parse.urlencode(dict(token=token, content=content,
            format="json", returnFormat="json", **options)).encode("utf-8")
    try:
        request = urllib.request.Request(API_URL, data=body, method="POST")
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.load(response)
    except Exception:
        raise Stop("REDCap request failed. No automatic retry.") from None
    if isinstance(result, dict) and ("error" in result or "errors" in result):
        raise Stop("REDCap rejected the request; no automatic retry.")
    return result

def read(client):
    raw = client("record", action="export", type="flat", rawOrLabel="raw",
                 **{f"fields[{i}]": field for i,field in enumerate(FIELDS)})
    if not isinstance(raw, list):
        raise Stop("Unexpected REDCap record export.")
    by_id = {}
    for r in raw:
        if not isinstance(r, dict):
            raise Stop("Malformed REDCap response.")
        rid = str(r.get("record_id", ""))
        if not rid or rid in by_id:
            raise Stop("Missing or duplicate REDCap record ID.")
        by_id[rid] = {k:str(r.get(k, "") or "") for k in FIELDS}
    return by_id

def verify_baseline(records, allow_released=False):
    if len(records)!=1114 or len(NEW_IDS.intersection(records))!=339:
        raise Stop("REDCap record count or recovered ID set has changed.")
    rows = [records[rid] for rid in sorted(NEW_IDS)]
    titled=[r for r in rows if r["title"].strip()]
    blank=[r for r in rows if not r["title"].strip()]
    if len(titled)!=334 or len(blank)!=5:
        raise Stop("Approved title set changed (334 titled + 5 blank required).")
    years=collections.Counter()
    for r in rows:
        match=re.match(r"^Presentation year (202[0-6])\b",r["source_refs"])
        if not match:
            raise Stop("Missing or unexpected presentation-year provenance.")
        years[match.group(1)]+=1
        if (r["curation_status"]!="1" or r["completion_year"].strip() or
                any(r[field]!="0" for field in
                    ("public_author","public_abstract","public_report"))):
            raise Stop("Curated status, year or privacy flags differ from approved import.")
        if r["public_catalogue"] not in (("0","1") if allow_released and r["title"].strip() else ("0",)):
            raise Stop("Unexpected public visibility flag.")
    if dict(years)!=EXPECTED_YEARS:
        raise Stop("Presentation-year distribution differs from 2020–2026 approved recovery.")
    return titled, blank

def verify_project(client):
    project=client("project")
    if not isinstance(project,dict) or str(project.get("project_id"))!="224":
        raise Stop("Connected token does not resolve to Project 224.")
    meta=client("metadata")
    if not isinstance(meta,list) or not set(FIELDS).issubset(
        {m.get("field_name") for m in meta if isinstance(m,dict)}):
        raise Stop("Live Project 224 dictionary differs from expected release fields.")

def execute(client, approval):
    if approval!=APPROVAL:
        raise Stop("Exact 334-title authorization phrase absent; no writes.")
    verify_project(client)
    live=read(client)
    titled,blank=verify_baseline(live)
    changes=[{"record_id":r["record_id"],"public_catalogue":"1"} for r in titled]
    written=0
    for offset in range(0,len(changes),20):
        batch=changes[offset:offset+20]
        current=read(client)
        verify_baseline(current,allow_released=True)
        for change in batch:
            rid=change["record_id"]
            if current[rid]!=live[rid] or current[rid]["public_catalogue"]!="0":
                raise Stop("A target record changed during release; stopped before batch.")
        response=client("record",action="import",type="flat",
                       overwriteBehavior="normal",forceAutoNumber="false",
                       returnContent="count",
                       data=json.dumps(batch,ensure_ascii=False))
        if not isinstance(response,dict) or str(response.get("count"))!=str(len(batch)):
            raise Stop("Unexpected REDCap write count; do not retry.")
        after=read(client)
        for change in batch:
            rid=change["record_id"]
            expected=dict(current[rid])
            expected["public_catalogue"]="1"
            if after.get(rid)!=expected:
                raise Stop("Readback differs from authorized one-field change; do not retry.")
            live[rid]=expected
        written+=len(batch)
    final=read(client)
    verify_baseline(final,allow_released=True)
    if (sum(final[rid]["public_catalogue"]=="1" for rid in NEW_IDS)!=334 or
            any(final[r["record_id"]]["public_catalogue"]!="0" for r in blank)):
        raise Stop("Final 334-title visibility check failed.")
    return {"project_id_verified":True, "total_records":len(final),
        "recovered_records":339, "titled_approved":334, "untitled_held":5,
        "records_changed":written, "field_changed":"public_catalogue",
        "curation_status_preserved":True, "public_author_remains_zero":True,
        "readback_verified":True}

def main():
    token=os.getenv(TOKEN_ENV,"")
    approval=os.getenv("PROJECT224_TITLE_RELEASE_APPROVAL","")
    def client(content,**options):
        return api(token,content,**options)
    print(json.dumps(execute(client,approval),indent=2))

if __name__=="__main__":
    try:
        main()
    except Stop as error:
        print("PROJECT 224 TITLE RELEASE SAFETY STOP: "+str(error),file=sys.stderr)
        sys.exit(2)
