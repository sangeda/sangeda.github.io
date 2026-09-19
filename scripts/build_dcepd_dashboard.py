#!/usr/bin/env python3
"""Read-only DCEPD reporting. Raw records stay in memory; only aggregates publish."""
import argparse, collections, csv, html, json, os, re, sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
ROOT = Path(__file__).resolve().parents[1]
API = 'https://utafiti.muhas.ac.tz/api/'
F75 = ['record_id','course_name','course_code','course_department_code','course_school_code','public_catalogue','run_start_date','run_end_date','run_participants','run_department_code','run_school_code']
F79 = ['record_id','applied_course_id','application_date','residence_region','country_of_residence']
L75 = ['Record ID','Course name','Course code','Department','School / institute / directorate','Listed in public catalogue?','Run start date','Run end date','Number of participants','Run department','Run School code']
L79 = ['Record ID','Short course applying for','Application date','Region of residence (Tanzania applicants) / Foreigner','Country of residence (if Foreigner selected above)']

def request(token, content, params=None):
    body=dict(token=token,content=content,format='json',returnFormat='json',**(params or {}))
    try:
        with urlopen(Request(API,data=urlencode(body).encode()),timeout=180) as r: data=json.load(r)
    except Exception:
        raise ValueError('REDCap export failed; no source records or credentials logged.') from None
    if not isinstance(data,list) or any(not isinstance(x,dict) for x in data):
        raise ValueError('REDCap did not return a record list.')
    return data

def fetch(project, fields):
    token=os.environ.get(f'REDCAP_PROJECT{project}_TOKEN','').strip()
    if not token: raise ValueError(f'Missing REDCAP_PROJECT{project}_TOKEN secret.')
    md={m['field_name']:m for m in request(token,'metadata')}
    if not set(fields)<=md.keys():raise ValueError(f'Project {project} schema changed; required reporting fields missing.')
    params=dict(action='export',type='flat',rawOrLabel='label',rawOrLabelHeaders='raw',exportSurveyFields='false',exportDataAccessGroups='false')
    params.update({f'fields[{i}]':f for i,f in enumerate(fields)})
    return request(token,'record',params)

def seed(path, fields, labels):
    with path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if not set(labels)<=set(reader.fieldnames):raise ValueError('Seed schema mismatch.')
        return [{**{a:r[b].strip() for a,b in zip(fields,labels)},'redcap_repeat_instrument':r.get('Repeat Instrument',''),'redcap_repeat_instance':r.get('Repeat Instance','')} for r in reader]

def parsedate(s):
    if not s:return None
    try:return date.fromisoformat(s)
    except ValueError:
        try:return datetime.strptime(s,'%d-%m-%Y').date()
        except ValueError:return None

def period(d):
    if not d:return ('Unknown','Unknown','Unknown')
    start=d.year if d.month>=7 else d.year-1
    return (str(d.year),f'{start}/{str(start+1)[-2:]}',f'Q{((d.month-7)%12)//3+1}')

def number(s):
    if not str(s).strip():return None
    try:
        n=float(s)
        return int(n) if n>=0 and n.is_integer() else None
    except ValueError:return None

def build(r75,r79,stamp,source,asof):
    courses={}; codes=collections.defaultdict(list); qc=collections.Counter()
    for r in r75:
        if r.get('redcap_repeat_instrument'):continue
        rid=r.get('record_id','').strip()
        if not rid or rid in courses:raise ValueError('Missing or duplicate Project 75 master ID.')
        c=dict(id=rid,course=r['course_name'].strip() or 'Untitled course',code=r['course_code'].strip(),school=r['course_school_code'].strip() or 'Unknown',department=r['course_department_code'].strip() or 'Unknown',listed=r['public_catalogue'].strip().lower()=='yes')
        courses[rid]=c
        if c['code']:codes[c['code']].append(c)
    if not courses:raise ValueError('Empty registry; refusing to replace dashboard.')
    delivery={}; seen=set()
    for r in r75:
        instrument=r.get('redcap_repeat_instrument','')
        if not instrument:continue
        if instrument not in ('course_run_log','Course Run Log'):
            qc['other_repeat_rows']+=1;continue
        key=(r['record_id'],r.get('redcap_repeat_instance',''))
        if key in seen:raise ValueError('Duplicate Run identity.')
        seen.add(key)
        c=courses.get(r['record_id'])
        if not c:qc['orphan_runs']+=1;continue
        d=parsedate(r['run_start_date']);end=parsedate(r['run_end_date']);n=number(r['run_participants'])
        if d is None:qc['runs_without_valid_start']+=1
        if r['run_participants'] and n is None:qc['invalid_attendance_values']+=1
        if end and d and end<d:qc['run_end_before_start']+=1
        state='Future-dated' if d and d>asof else 'Recorded'
        yr,fy,q=period(d)
        school=r['run_school_code'].strip() or c['school'];dep=r['run_department_code'].strip() or c['department']
        key=(c['id'],school,dep,yr,fy,q,state)
        if key not in delivery:delivery[key]=dict(course_id=c['id'],course=c['course'],school=school,department=dep,year=yr,fy=fy,quarter=q,state=state,sessions=0,attendance=0,reported=0,unknown=0)
        v=delivery[key];v['sessions']+=1
        if n is None:v['unknown']+=1
        else:v['attendance']+=n;v['reported']+=1
    unmatched_labels=collections.Counter()
    apps={};geo=collections.Counter();countries=collections.Counter();seen=set();unmatched=0
    for r in r79:
        if r.get('redcap_repeat_instrument'):raise ValueError('Unexpected repeating Project 79 schema; review counting rules.')
        rid=r['record_id'].strip()
        if not rid or rid in seen:raise ValueError('Missing or duplicate application record ID.')
        seen.add(rid)
        selection=r['applied_course_id'].strip()
        # Resolve the code in the labelled lookup. Never equate Project 79 choice IDs with registry IDs.
        code=selection.split('|',1)[0].strip()
        matches=codes.get(code,[])
        c=matches[0] if len(matches)==1 else None
        if not c:
            unmatched+=1;unmatched_labels[selection or 'No course selected']+=1
        d=parsedate(r['application_date'])
        if not d:qc['applications_without_valid_date']+=1
        if d and d>asof:qc['applications_future_dated']+=1
        yr,fy,q=period(d)
        key=((c or {}).get('id','unmatched'),yr,fy,q)
        if key not in apps:apps[key]=dict(course_id=key[0],course=(c or {}).get('course','Unmatched / unselected course'),school=(c or {}).get('school','Unknown'),department=(c or {}).get('department','Unknown'),year=yr,fy=fy,quarter=q,applications=0)
        apps[key]['applications']+=1
        region=r['residence_region'].strip() or 'Unknown'
        geo[region]+=1
        if region=='Foreigner':countries[r['country_of_residence'].strip() or 'Unknown']+=1
    qc['unmatched_applications']=unmatched
    qc['duplicate_registry_course_codes']=sum(len(x)>1 for x in codes.values())
    # Public applications are aggregated; cells below 5 are withheld. Geography is an independent all-period view.
    publicapps=[]
    for v in apps.values():
        publicapps.append({**v,'applications':v['applications'] if v['applications']>=5 else None,'withheld':v['applications']<5})
    def publicgeo(counter):
        rows=[dict(location=k,applications=n) for k,n in counter.items() if n>=5]
        small=sum(n for n in counter.values() if n<5)
        if small:rows.append(dict(location='Other small groups (combined)',applications=small if small>=5 else None))
        return sorted(rows,key=lambda x:-(x['applications'] or 0))
    metadata=dict(schema_version=1,source=source,source_at=stamp,as_of=asof.isoformat(),registered_courses=len(courses),listed_courses=sum(c['listed'] for c in courses.values()),application_records=len(r79),notes='Attendance is recorded attendances, not unique people or completion. Runs are assigned by start date; application periods use application date. Missing counts stay unknown. Application cells below 5 are withheld; geography covers the whole snapshot.')
    public=dict(metadata=metadata,courses=list(courses.values()),delivery=list(delivery.values()),applications=publicapps,geography=publicgeo(geo),countries=publicgeo(countries))
    management=dict(metadata=metadata,courses=list(courses.values()),delivery=list(delivery.values()),applications=list(apps.values()),geography=[dict(location=k,applications=n) for k,n in geo.most_common()],countries=[dict(location=k,applications=n) for k,n in countries.most_common()],quality=dict(qc),unmatched_course_selections=dict(unmatched_labels))
    return public,management

def render(data,management=False):
    text=(ROOT/'scripts/dcepd_dashboard_template.html').read_text()
    title='DCEPD management review' if management else 'MUHAS DCEPD activity dashboard'
    payload=json.dumps(data,ensure_ascii=False).replace('<','\\u003c')
    boundary=ROOT/'dcepd-dashboard/boundaries/tanzania-regions.geojson'
    if boundary.exists():
        geo=boundary.read_text().replace('<','\\u003c')
        mapjs=(ROOT/'scripts/dcepd_map.js').read_text()
        text=text.replace('</body>','<script id="map-boundaries" type="application/json">'+geo+'</script><script>'+mapjs+'</script></body>')
    return text.replace('{{TITLE}}',title).replace('{{ACCESS}}','Local management review · not published' if management else 'Public aggregate reporting').replace('{{DATA}}',payload).replace('{{STAMP}}',html.escape(data['metadata']['source_at'])).replace('{{SOURCE}}',html.escape(data['metadata']['source'])).replace('{{REGISTRY_COUNT}}',str(data['metadata']['registered_courses']))

def main():
    p=argparse.ArgumentParser();p.add_argument('--seed75',type=Path);p.add_argument('--seed79',type=Path);p.add_argument('--source-at');p.add_argument('--management-output',type=Path);args=p.parse_args()
    if bool(args.seed75)!=bool(args.seed79):p.error('Both seed files are required.')
    stamp=args.source_at or datetime.now(timezone.utc).isoformat(timespec='seconds')
    if args.seed75:
        if not args.source_at:p.error('Seed snapshots require --source-at.')
        r75=seed(args.seed75,F75,L75);r79=seed(args.seed79,F79,L79);source='Supplied Project 75 and Project 79 snapshots'
    else:r75=fetch(75,F75);r79=fetch(79,F79);source='Project 75 and Project 79 APIs'
    public,management=build(r75,r79,stamp,source,datetime.fromisoformat(stamp).date())
    out=ROOT/'dcepd-dashboard';out.mkdir(exist_ok=True)
    # All validation precedes writing; workflow publishes only after successful completion.
    (out/'summary.json').write_text(json.dumps(public,ensure_ascii=False,indent=2)+'\n')
    (out/'index.html').write_text(render(public))
    if args.management_output:
        target=args.management_output.resolve()
        if target.is_relative_to(ROOT):raise ValueError('Management output must be outside the public repository.')
        target.parent.mkdir(parents=True,exist_ok=True);target.write_text(render(management,True))
    print('Generated aggregate dashboard:',len(public['courses']),'courses;',sum(x['sessions'] for x in public['delivery']),'Runs;',len(r79),'applications. No source records saved.')
if __name__=='__main__':
    try:main()
    except ValueError as e:sys.exit(str(e))
