#!/usr/bin/env python3
"""Guarded REDCap Project 224 importer. Private CSV is passed only via GitHub Actions secret."""
import argparse,base64,csv,gzip,hashlib,io,json,os,re,sys,urllib.parse,urllib.request

API_URL="https://utafiti.muhas.ac.tz/api/"
EXPECTED_SHA256="a9fe6dd462975ba005f21dcbdbebf2c3ae528708cde50b7c0c1338bb644d9225"
DATA_ENV="BPHARM_PROJECT224_RECOVERY_DATA_GZ_B64"
TOKEN_ENV="REDCAP_PROJECT224_TOKEN"
FIELDS=["record_id","student_name","regno","completion_year","title","source_refs",
        "report_status","curation_status","public_catalogue","public_author",
        "public_abstract","public_report","curation_notes"]
RECORD_IDS=[f"BPH{i:06d}" for i in range(802,1141)]
REGNO=re.compile(r"\d{4}-\d{2}-\d{5}\Z")
CONFIRMATIONS={"first_five":"IMPORT PROJECT 224 FIRST FIVE",
               "remaining":"IMPORT PROJECT 224 REMAINING"}

class StopImport(Exception):
    pass

def load_private_csv(secret):
    if not secret:raise StopImport(f"Missing temporary GitHub secret {DATA_ENV}; no import performed.")
    try:data=gzip.decompress(base64.b64decode(secret,validate=True))
    except (ValueError,OSError,EOFError):
        raise StopImport("Private dataset secret is not valid base64-encoded gzip.") from None
    if hashlib.sha256(data).hexdigest()!=EXPECTED_SHA256:
        raise StopImport("Private CSV SHA-256 differs from approved staging file.")
    try:
        reader=csv.DictReader(io.StringIO(data.decode("utf-8-sig"),newline=""))
        if reader.fieldnames!=FIELDS:raise StopImport("Private CSV field names/order differ from approved staging file.")
        rows=list(reader)
    except UnicodeError:raise StopImport("Invalid UTF-8 private CSV.") from None
    if len(rows)!=339 or [r["record_id"] for r in rows]!=RECORD_IDS:
        raise StopImport("Private CSV count/IDs do not match BPH000802–BPH001140.")
    if sum(not r["title"].strip() for r in rows)!=5:
        raise StopImport("Expected exactly five intentionally blank titles.")
    if sum(not r["regno"].strip() for r in rows)!=138:
        raise StopImport("Expected exactly 138 blank registration numbers.")
    regnos=set()
    for r in rows:
        reg=r["regno"].strip()
        if reg:
            if not REGNO.fullmatch(reg) or reg in regnos:
                raise StopImport("Invalid or duplicate registration number.")
            regnos.add(reg)
        if r["completion_year"].strip():raise StopImport("Completion years must remain blank.")
        if any(r[f].strip()!="0" for f in ("public_catalogue","public_author","public_abstract","public_report")):
            raise StopImport("Unexpected public visibility flag.")
        if r["curation_status"].strip()!="1" or r["report_status"].strip()!="0":
            raise StopImport("Unexpected REDCap status code.")
        if None in r:raise StopImport("Unexpected extra CSV columns.")
    return rows

def api_call(token,content,**opts):
    body=urllib.parse.urlencode(dict(token=token,content=content,format="json",returnFormat="json",**opts)).encode()
    try:
        req=urllib.request.Request(API_URL,data=body,method="POST")
        with urllib.request.urlopen(req,timeout=120) as resp: result=json.load(resp)
    except Exception:raise StopImport("REDCap API request failed; stop and inspect privately.") from None
    if isinstance(result,dict) and ("error" in result or "errors" in result):
        raise StopImport("REDCap API reported an error; no retry attempted.")
    return result

def read_live(client,fields):
    project=client("project")
    if not isinstance(project,dict) or str(project.get("project_id"))!="224":
        raise StopImport("Token does not resolve to Project 224.")
    meta=client("metadata")
    if not isinstance(meta,list) or not set(FIELDS).issubset(
            {m.get("field_name") for m in meta if isinstance(m,dict)}):
        raise StopImport("Live Project 224 dictionary is missing required fields.")
    raw=client("record",action="export",type="flat",rawOrLabel="raw",
               **{f"fields[{i}]":v for i,v in enumerate(fields)})
    if not isinstance(raw,list):raise StopImport("Unexpected live record export format.")
    records={}
    for entry in raw:
        if not isinstance(entry,dict):raise StopImport("Malformed live record data.")
        rid=str(entry.get("record_id",""))
        if not rid or rid in records:raise StopImport("Blank or duplicate live record ID.")
        records[rid]=entry
    return records

def check_equal(actual,expected):
    return actual is not None and all(
        str(actual.get(k,"")).strip()==str(expected[k]).strip() for k in FIELDS)

def write_and_check(client,batch):
    result=client("record",action="import",type="flat",overwriteBehavior="normal",
                  forceAutoNumber="false",returnContent="count",
                  data=json.dumps(batch,ensure_ascii=False))
    if not isinstance(result,dict) or str(result.get("count",""))!=str(len(batch)):
        raise StopImport("Unexpected REDCap import count; inspect before retry.")
    live=read_live(client,FIELDS)
    if not all(check_equal(live.get(r["record_id"]),r) for r in batch):
        raise StopImport("Post-import readback mismatch; no retries.")
    return len(batch)

def perform(rows,client,operation,confirmation):
    if operation not in ("preflight","first_five","remaining"):
        raise StopImport("Unknown operation.")
    if operation!="preflight" and confirmation!=CONFIRMATIONS[operation]:
        raise StopImport("Exact write confirmation not supplied.")
    live=read_live(client,["record_id"] if operation!="remaining" else FIELDS)
    result={"project_id_verified":True,"source_hash_verified":True,
            "expected_import_count":len(rows),"live_record_count_before":len(live),
            "new_id_collisions_before":sum(r["record_id"] in live for r in rows),
            "operation":operation}
    if operation=="preflight":
        result["can_start_five_record_import"]=result["new_id_collisions_before"]==0
        result["records_written"]=0
        return result
    if operation=="first_five":
        if any(r["record_id"] in live for r in rows):
            raise StopImport("A proposed ID is occupied; no writes attempted.")
        current=read_live(client,["record_id"])
        if any(r["record_id"] in current for r in rows):
            raise StopImport("ID collision before test batch.")
        result["records_written"]=write_and_check(client,rows[:5])
        result["first_five_readback_verified"]=True
        return result
    if not all(check_equal(live.get(r["record_id"]),r) for r in rows[:5]):
        raise StopImport("First five live records differ from staged CSV.")
    if any(r["record_id"] in live for r in rows[5:]):
        raise StopImport("A remaining ID is occupied; no writes attempted.")
    written=0
    for start in range(5,len(rows),20):
        batch=rows[start:start+20]
        current=read_live(client,["record_id"])
        if any(r["record_id"] in current for r in batch):
            raise StopImport("ID collision before batch; stop for reconciliation.")
        written+=write_and_check(client,batch)
    result["records_written"]=written
    result["remaining_readback_verified"]=True
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--operation",choices=("preflight","first_five","remaining"),default="preflight")
    parser.add_argument("--confirm",default="")
    args=parser.parse_args()
    rows=load_private_csv(os.environ.get(DATA_ENV,""))
    token=os.environ.get(TOKEN_ENV,"")
    if not token:raise StopImport("Missing REDCAP_PROJECT224_TOKEN secret.")
    def client(content,**opts):return api_call(token,content,**opts)
    print(json.dumps(perform(rows,client,args.operation,args.confirm),indent=2))

if __name__=="__main__":
    try:main()
    except StopImport as error:
        print(f"PROJECT 224 SAFETY STOP: {error}",file=sys.stderr)
        sys.exit(2)
