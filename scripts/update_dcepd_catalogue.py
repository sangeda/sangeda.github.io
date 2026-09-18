#!/usr/bin/env python3
"""Read-only Project 75 catalogue. Standard library only; never export applicants."""
import argparse
import csv
import html
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
APPLY_URL = 'https://utafiti.muhas.ac.tz/surveys/?s=RCJLANHXKKMKXC7W'
API_URL = 'https://utafiti.muhas.ac.tz/api/'
FIELDS = ['record_id', 'course_name', 'course_code', 'public_catalogue',
          'course_department_code', 'course_school_code', 'fee_per_person_tsh', 'cpd_points']
LABELS = dict(zip(FIELDS, ['Record ID', 'Course name', 'Course code', 'Listed in public catalogue?',
    'Department', 'School / institute / directorate', 'Fee per person (TZS)', 'CPD points']))

def normalise(text):
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().lower()).split())

def api_export(token, content, extra=None):
    body = dict(token=token, content=content, format='json', returnFormat='json')
    body.update(extra or {})
    try:
        with urlopen(Request(API_URL, data=urlencode(body).encode()), timeout=180) as response:
            value = json.load(response)
    except Exception:
        raise ValueError('Project 75 export failed. Check the API endpoint, token and export permissions; existing catalogue retained.') from None
    if not isinstance(value, list) or any(not isinstance(r, dict) for r in value):
        raise ValueError('Project 75 did not return a valid record list; existing catalogue retained.')
    return value

def fetch_records():
    token = os.environ.get('REDCAP_PROJECT75_TOKEN', '').strip()
    if not token:
        raise ValueError('Set the REDCAP_PROJECT75_TOKEN repository secret to enable the read-only refresh.')
    metadata = api_export(token, 'metadata')
    md = {m['field_name']: m for m in metadata}
    if not set(FIELDS).issubset(md):
        raise ValueError('Required Project 75 catalogue fields are missing.')
    field = md['public_catalogue']
    if field['field_type'] == 'yesno':
        yes_code = '1'
    else:
        options = [x.split(',', 1) for x in field.get('select_choices_or_calculations', '').split('|')]
        yes = [v[0].strip() for v in options if len(v) == 2 and v[1].strip().lower() == 'yes']
        if len(yes) != 1:
            raise ValueError('Cannot verify the stored Yes value for public_catalogue.')
        yes_code = yes[0]
    if not re.fullmatch(r'[A-Za-z0-9_]+', yes_code):
        raise ValueError('Unexpected catalogue choice code.')
    params = dict(action='export', type='flat', rawOrLabel='label', rawOrLabelHeaders='raw',
                  exportSurveyFields='false', exportDataAccessGroups='false',
                  filterLogic=f"[public_catalogue] = '{yes_code}'")
    params.update({f'fields[{i}]': f for i, f in enumerate(FIELDS)})
    records = api_export(token, 'record', params)
    return records

def build(records, source, source_at, taxonomy):
    courses, seen = [], set()
    for row in records:
        if row.get('redcap_repeat_instrument', '').strip():
            continue
        if row.get('public_catalogue', '').strip().lower() != 'yes':
            continue
        if not set(FIELDS).issubset(row):
            raise ValueError('Incomplete catalogue record schema.')
        rid = row['record_id'].strip()
        if not rid or rid in seen:
            raise ValueError('Missing or duplicate master-course ID.')
        seen.add(rid)
        title = ' '.join(row['course_name'].split())
        if not title:
            raise ValueError('A listed course has no title; correct the source record.')
        classification = taxonomy['courses'].get(rid, {})
        # Overrides are bound to their source title so edits cannot retain stale categories.
        if classification.get('source_title') != title:
            classification = {}
        category = classification.get('category', 'Other courses')
        tags = set(classification.get('tags', []))
        norm_title = normalise(title)
        for rule in taxonomy['keyword_rules']:
            if re.search(rule['pattern'], norm_title):
                tags.update(rule['tags'])
        courses.append(dict(id=rid, title=classification.get('display_title', title), source_title=title,
            code=row['course_code'].strip(), school=row['course_school_code'].strip(),
            department=row['course_department_code'].strip(), fee_tzs=row['fee_per_person_tsh'].strip(),
            cpd_points=row['cpd_points'].strip(), category=category, tags=sorted(tags), apply_url=APPLY_URL))
    courses.sort(key=lambda c: normalise(c['title']))
    return dict(schema_version=1, source=source, source_at=source_at,
                api_refreshed_at=source_at if source == 'Project 75 API' else None,
                count=len(courses), courses=courses)

def render_card(c):
    e = lambda x: html.escape(str(x), quote=True)
    tags = ''.join(f'<span class="tag">{e(t)}</span>' for t in c['tags'])
    search = normalise(' '.join([c['title'], c['source_title'], c['code'], c['school'], c['department'], c['category'], *c['tags']]))
    details = ''.join(f'<div><dt>{label}</dt><dd>{e(value)}</dd></div>' for label, value in [
        ('Course code', c['code'] or 'Not yet recorded'), ('Organising unit', c['department'] or 'Not recorded'),
        ('School / institute / directorate', c['school'] or 'Not recorded'),
        ('Recorded fee (TZS)', c['fee_tzs'] or 'Confirm with DCEPD'),
        ('CPD points', c['cpd_points'] or 'Confirm with DCEPD')])
    return f'''<article class="course" id="course-{e(c['id'])}" data-category="{e(c['category'])}" data-school="{e(c['school'])}" data-search="{e(search)}">
    <p class="category">{e(c['category'])}</p><h3>{e(c['title'])}</h3>
    <p class="unit">{e(c['school'] or 'MUHAS')}</p><div class="tags">{tags}</div>
    <details><summary>Course details</summary><dl>{details}</dl><p class="fine">Confirm the current fee, intake dates, delivery mode and CPD recognition before making arrangements.</p></details>
    <div class="card-actions"><a class="apply" href="{APPLY_URL}" aria-label="Apply: {e(c['title'])}">Apply <span aria-hidden="true">↗</span></a><span>Select this course in the form</span></div></article>'''

def save(data):
    out = ROOT / 'dcepd-courses'
    template = (ROOT / 'scripts/dcepd_catalogue_template.html').read_text()
    categories = sorted({c['category'] for c in data['courses']})
    schools = sorted({c['school'] for c in data['courses'] if c['school']})
    options = lambda values: ''.join(f'<option value="{html.escape(v, quote=True)}">{html.escape(v)}</option>' for v in values)
    replacements = {'CARDS': '\n'.join(render_card(c) for c in data['courses']), 'COUNT': str(data['count']),
        'CATEGORY_OPTIONS': options(categories), 'SCHOOL_OPTIONS': options(schools),
        'SOURCE': html.escape(data['source']), 'SOURCE_AT': html.escape(data['source_at']),
        'REFRESH_LABEL': 'Last successful API refresh' if data['api_refreshed_at'] else 'Registry export dated',
        'CATEGORY_COUNT': str(len(categories)), 'SCHOOL_COUNT': str(len(schools))}
    for key, value in replacements.items():
        template = template.replace('{{' + key + '}}', value)
    out.mkdir(exist_ok=True)
    # Build in memory first. Only successful extraction/validation replaces published outputs.
    for path, value in [(out/'catalogue.json', json.dumps(data, ensure_ascii=False, indent=2)+'\n'), (out/'index.html', template)]:
        tmp = path.with_suffix(path.suffix + '.tmp')
        tmp.write_text(value, encoding='utf-8')
        tmp.replace(path)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed-csv', type=Path)
    parser.add_argument('--source-at')
    args = parser.parse_args()
    if args.seed_csv:
        if not args.source_at:
            parser.error('--source-at is required with --seed-csv')
        with args.seed_csv.open(encoding='utf-8-sig', newline='') as f:
            records = [{**{k: r[v] for k, v in LABELS.items()}, 'redcap_repeat_instrument': r['Repeat Instrument']} for r in csv.DictReader(f)]
        source, stamp = 'Supplied Project 75 export', args.source_at
    else:
        records = fetch_records()
        source, stamp = 'Project 75 API', datetime.now(timezone.utc).isoformat(timespec='seconds')
    taxonomy = json.loads((ROOT/'scripts/dcepd_taxonomy.json').read_text())
    data = build(records, source, stamp, taxonomy)
    save(data)
    print(f"Published catalogue contains {data['count']} listed master-course records.")

if __name__ == '__main__':
    try:
        main()
    except ValueError as exc:
        sys.exit(str(exc))
