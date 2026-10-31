#!/usr/bin/env python3
"""Build the public profile collections; add/update a record using validated JSON."""
import argparse
import collections
import datetime as dt
import html
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {
    'student': ('name', 'level', 'institution', 'year', 'status', 'title'),
    'event': ('name', 'start_date', 'end_date', 'city', 'country', 'sponsor', 'role', 'description'),
}
FILES = {'student': 'students', 'event': 'events'}
e = html.escape


def validate(kind, row):
    allowed = set(FIELDS[kind]) | {'id'}
    if set(row) - allowed:
        raise ValueError('Unknown fields: ' + ', '.join(sorted(set(row) - allowed)))
    if any(not isinstance(v, str) for v in row.values()):
        raise ValueError('All field values must be text.')
    if not row.get('name', '').strip():
        raise ValueError('A name is required.')
    if row.get('id') and not re.fullmatch(r'(SUP|EVT)\d{4,}', row['id']):
        raise ValueError('Invalid record ID.')
    if kind == 'student':
        if row.get('level') not in ('BPharm', 'MPharm', 'MSc', 'PhD', 'Other'):
            raise ValueError('Level must be BPharm, MPharm, MSc, PhD or Other.')
        if row.get('status') not in ('Completed', 'In Progress', 'Unknown'):
            raise ValueError('Status must be Completed, In Progress or Unknown.')
        if row.get('year') and row['year'] not in ('Ongoing', 'Unknown') and not re.fullmatch(r'(19|20)\d{2}', row['year']):
            raise ValueError('Year must be YYYY, Ongoing, Unknown or blank.')
    else:
        for key in ('start_date', 'end_date'):
            if row.get(key):
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', row[key]):
                    raise ValueError('Dates must be YYYY-MM-DD.')
                dt.date.fromisoformat(row[key])
        if row.get('end_date') and not row.get('start_date'):
            raise ValueError('End date requires a start date.')
        if row.get('end_date') and row['end_date'] < row['start_date']:
            raise ValueError('End date precedes start date.')


def load(kind, root=ROOT):
    data = json.loads((root / 'data/profile' / (FILES[kind] + '.json')).read_text())
    ids = []
    for row in data['records']:
        validate(kind, row)
        ids.append(row['id'])
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate record IDs.')
    return data


def change(kind, action, payload, record_id=None, root=ROOT):
    data = load(kind, root)
    if not isinstance(payload, dict) or 'id' in payload:
        raise ValueError('Record must be a JSON object without id; use --id for updates.')
    if action == 'add':
        row = {key: '' for key in FIELDS[kind]}
        row.update(payload)
        validate(kind, row)
        if any(all(r.get(k, '').strip().casefold() == row.get(k, '').strip().casefold() for k in FIELDS[kind]) for r in data['records']):
            raise ValueError('This exact record already exists; nothing was added.')
        prefix = 'SUP' if kind == 'student' else 'EVT'
        number = max([int(r['id'][3:]) for r in data['records']] or [0]) + 1
        row = {'id': prefix + f'{number:04d}', **row}
        data['records'].append(row)
    else:
        matches = [r for r in data['records'] if r['id'] == record_id]
        if len(matches) != 1:
            raise ValueError('Update requires an existing --id.')
        row = {**matches[0], **payload}
        validate(kind, row)
        matches[0].update(row)
    data['updated_at'] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    path = root / 'data/profile' / (FILES[kind] + '.json')
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)
    return row['id']


def select(key, label, values):
    options = ''.join(f'<option value="{e(v, quote=True)}">{e(v)}</option>' for v in values)
    return f'<label>{label}<select name="{key}" data-filter="{key}"><option value="">All</option>{options}</select></label>'


def date_text(value):
    return dt.date.fromisoformat(value).strftime('%d %b %Y') if value else 'Date not recorded'


def build_page(kind, data, root):
    student = kind == 'student'
    rows = data['records']
    route = 'supervision' if student else 'events'
    title = 'Student supervision' if student else 'Events & academic engagement'
    lead = ('Research mentorship across pharmacy, microbiology, bioinformatics and health systems. Explore the supplied supervision record by student, research topic, degree and institution.' if student else 'Conferences, workshops, training and collaborative activities connecting research, professional practice and academic capacity building.')
    if student:
        levels = collections.Counter(r['level'] for r in rows)
        stats = [(len(rows), 'supervision records'), (levels['PhD'], 'PhD records'), (sum(levels[k] for k in ('MSc', 'MPharm')), 'master’s records'), (levels['BPharm'], 'BPharm records')]
        filters = [('level', 'Degree level'), ('status', 'Recorded status'), ('year', 'Recorded year'), ('institution', 'Institution')]
        note = 'This is a record-based list, not a verified count of unique students. Possible repeated names and project variants are retained pending review. Degree, year and status follow the supplied record; “In Progress” has not been independently reconfirmed. Master’s entries in the initial file are labelled MSc.'
    else:
        stats = [(len(rows), 'activity records'), (len({r['country'] for r in rows if r['country']}), 'countries recorded'), (sum(r['role']=='Facilitator' for r in rows), 'facilitator records'), (sum(not r['start_date'] for r in rows), 'dates not recorded')]
        filters = [('year', 'Year'), ('country', 'Country'), ('role', 'Recorded role')]
        note = 'Dates and roles follow the supplied CV activity list. Blank dates remain unknown; a missing end date is not treated as confirmation of a one-day event. Related or overlapping activities are retained as separate records. “Participant” does not imply a speaking role.'
    display = []
    for r in rows:
        facets = {key: r.get(key, '') or 'Not recorded' for key, _ in filters}
        if not student:
            facets['year'] = r['start_date'][:4] or 'Date not recorded'
        elif not r['year']:
            facets['year'] = 'Unknown'
        display.append((r, facets))
    controls = ''.join(select(key, label, sorted({f[key] for _, f in display}, reverse=key=='year')) for key, label in filters)
    cards = []
    for r, facets in display:
        attrs = ' '.join(f'data-{key}="{e(value, quote=True)}"' for key, value in facets.items())
        order = (r['year'] if r['year'].isdigit() else '') if student else r['start_date']
        if student:
            meta = f'<span class="record-badge">{e(r["level"])}</span><span>{e(r["status"])}</span><span>· {e(r["year"] or "Year not recorded")}</span>'
            body = f'<h2>{e(r["name"])}</h2><p class="record-details">{e(r["institution"] or "Institution not recorded")}</p><p class="project-title">{e(r["title"] or "Research title not recorded")}</p>'
        else:
            dates = date_text(r['start_date'])
            if r['end_date'] and r['end_date'] != r['start_date']:
                dates += ' – ' + date_text(r['end_date'])
            meta = f'<span class="record-badge">{e(r["role"] or "Role not recorded")}</span><span>{e(dates)}</span>'
            place = ', '.join(x for x in (r['city'], r['country']) if x) or 'Location not recorded'
            body = f'<h2>{e(r["name"])}</h2><p class="record-details">{e(place)}</p>'
            if r['description']: body += f'<p>{e(r["description"])}</p>'
            if r['sponsor']: body += f'<p class="record-details">Sponsor / project: {e(r["sponsor"])}</p>'
        cards.append(f'<article class="record-card" id="{r["id"]}" {attrs} data-date="{order}" data-name="{e(r["name"],quote=True)}"><div class="record-meta">{meta}</div>{body}<a class="record-id" href="#{r["id"]}" aria-label="Permanent link to record {r["id"]}">{r["id"]} ↗</a></article>')
    stats_html = ''.join(f'<div><strong>{number}</strong><span>{label}</span></div>' for number, label in stats)
    tabs = ''.join(f'<a href="/{url}/"'+(' aria-current="page"' if url==route else '')+f'>{label}</a>' for url,label in [('supervision','Student supervision'),('events','Events & engagement')])
    page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | Raphael Z. Sangeda</title><link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/assets/style.css"><link rel="stylesheet" href="/assets/profile-records.css">
<script src="/assets/profile-records.js" defer></script></head>
<body><a class="skip-link" href="#main">Skip to content</a>
<header class="site-header record-header"><div class="nav-wrap"><a class="brand" href="/"><span class="brand-mark">RZS</span>Raphael Z. Sangeda</a><nav class="record-nav" aria-label="Primary navigation"><a href="/">Profile</a><a href="/publications.html">Publications</a><a href="/supervision/" {'aria-current="page"' if student else ''}>Supervision</a><a href="/events/" {'aria-current="page"' if not student else ''}>Events</a></nav></div></header>
<main id="main" data-records="{route}"><section class="record-hero"><p class="eyebrow">Academic record · Raphael Z. Sangeda</p><h1>{title}</h1><p class="hero-lead">{lead}</p><div class="record-stats" aria-label="Full collection summary">{stats_html}</div></section>
<section class="records-main" aria-label="Search the collection"><nav class="record-tabs" aria-label="Academic collections">{tabs}</nav>
<form class="record-controls" id="record-filters" hidden data-enhanced><label class="search-field">Search {'student names, research titles or institutions' if student else 'events, cities, sponsors or keywords'}<input id="search" name="q" type="search" placeholder="{'Try HIV, antimicrobial resistance or a student name' if student else 'Try H3ABioNet, SickleInAfrica or digital health'}" autocomplete="off"></label>{controls}<label>Sort by<select id="sort" name="sort"><option value="newest">Newest recorded date</option><option value="oldest">Oldest recorded date</option><option value="name">Name A–Z</option></select></label></form>
<div class="record-toolbar"><p id="record-count" role="status" aria-live="polite">{len(rows)} records</p><div class="actions" hidden data-enhanced><button type="button" id="reset">Clear filters</button><button type="button" id="download">Download results · CSV</button></div></div>
<noscript><p>All records appear below. Enable JavaScript to use search, filters and downloads.</p></noscript><p class="record-empty" id="record-empty" hidden>No records match these filters. Try another keyword or clear the filters.</p>
<div class="record-list" id="record-list">{''.join(cards)}</div><p class="record-note">{note}</p><p class="record-note">Record collection updated: {e(data['updated_at'])}. Summary figures describe the full collection; the result count and CSV follow your filters.</p></section></main>
<footer class="record-footer"><a href="/">← Academic profile</a> · Prof. Raphael Z. Sangeda · MUHAS</footer>
<script type="application/json" id="record-data">{json.dumps(rows,ensure_ascii=False).replace('<', chr(92)+'u003c')}</script></body></html>'''
    directory = root / route
    directory.mkdir(exist_ok=True)
    (directory/'index.html').write_text(page, encoding='utf-8')



def refine_home(text):
    highlights = """<div class="hero-stats" aria-label="Academic profile highlights">
        <a class="highlight-link" href="/publications.html"><strong>150+</strong><span>peer-reviewed publications and book chapters</span><small>Explore publications ↗</small></a>
        <a class="highlight-link" href="/supervision/?level=BPharm"><strong>25+</strong><span>BPharm researchers supervised</span><small>Browse BPharm supervision ↗</small></a>
        <a class="highlight-link" href="#leadership"><strong>2001–</strong><span>academic service at MUHAS</span><small>Academic service &amp; leadership ↓</small></a>
        <a class="highlight-link" href="#education"><strong>3</strong><span>continents of academic training and collaboration</span><small>Education &amp; international engagement ↓</small></a>
      </div>
    </section>"""
    text = re.sub(r'<div class="hero-stats" aria-label="Academic profile highlights">.*?</section>', lambda _: highlights, text, count=1, flags=re.S)
    text = text.replace('<section class="section education">', '<section id="education" class="section education">')
    if 'academic-service-intro' not in text:
        text = text.replace('<h2>Academic leadership at MUHAS</h2>', '<h2>Academic leadership at MUHAS</h2><p id="academic-service-intro">Academic service at MUHAS since 2001, including teaching, research supervision and institutional leadership.</p>')
    if 'international-engagement-link' not in text:
        old = 'Training across pharmacy, microbiology, computing and biomedical sciences shaped an unusually integrative research practice.'
        new = 'Academic training spans Africa, Asia and Europe, across pharmacy, microbiology, computing and biomedical sciences. <a id="international-engagement-link" class="detail-link" href="/events/">Explore conferences, training and international engagement ↗</a>'
        text = text.replace(old, new)
    osp = 'https://muhas-osp.github.io/opportunities/'
    if '<a href="'+osp+'">OSP opportunities</a>' not in text:
        text = text.replace('<a href="/events/">Events</a>', '<a href="/events/">Events</a>\n        <a href="'+osp+'">OSP opportunities</a>', 1)
    if 'id="opportunities"' not in text:
        section = """<section id="opportunities" class="section split tinted"><div><p class="section-kicker">Research opportunities</p><h2>Find support for the next research idea.</h2></div><div class="prose"><p>Browse funding calls through the MUHAS OSP opportunities portal, alongside the publication and research resources linked from this profile.</p><a class="button primary" href="https://muhas-osp.github.io/opportunities/">Explore MUHAS OSP opportunities ↗</a></div></section>

    """
        text = text.replace('<section class="contact section">', section+'<section class="contact section">')
    return text

def build(root=ROOT):
    students = load('student', root)
    events = load('event', root)
    build_page('student', students, root)
    build_page('event', events, root)
    home = root/'index.html'
    if home.exists():
        text = home.read_text()
        levels = collections.Counter(r['level'] for r in students['records'])
        section = f'''<!-- PROFILE-RECORDS START -->
    <section id="mentorship" class="section split mentorship"><div><p class="section-kicker">Teaching &amp; mentorship</p><h2>Research mentorship, from question to evidence.</h2></div><div class="prose"><p>I teach and supervise undergraduate, master’s and PhD researchers and contribute to bioinformatics teaching at the African Institute for Mathematical Sciences and the University of Dar es Salaam. My mentorship links research questions with reproducible analysis, publication and practical public-health value.</p><div class="mentorship-stats"><div><strong>{levels['BPharm']}</strong><span>BPharm supervision records</span></div><div><strong>{sum(levels[k] for k in ('MSc','MPharm'))}</strong><span>master’s supervision records</span></div><div><strong>{levels['PhD']}</strong><span>PhD supervision records</span></div></div><p>Explore student research and the academic activities supporting this work. Counts describe supplied records, with possible repeats retained for review.</p><div class="profile-overview"><a href="/supervision/"><strong>Student supervision ↗</strong><span>Search names and topics; filter by degree, year, status and institution.</span></a><a href="/events/"><strong>Events &amp; engagement ↗</strong><span>{len(events['records'])} recorded activities. Explore conferences, workshops and training by year, country and role.</span></a></div></div></section>
    <!-- PROFILE-RECORDS END -->'''
        if '<!-- PROFILE-RECORDS START -->' in text:
            text = re.sub(r'<!-- PROFILE-RECORDS START -->.*?<!-- PROFILE-RECORDS END -->', lambda _: section, text, flags=re.S)
        else:
            text, n = re.subn(r'<section id="mentorship".*?</section>', lambda _: section, text, count=1, flags=re.S)
            if n != 1: raise ValueError('Homepage mentorship section not found.')
        if 'href="/assets/profile-records.css"' not in text:
            text = text.replace('</head>', '<link rel="stylesheet" href="/assets/profile-records.css">\n</head>')
        if '<a href="/events/">Events</a>' not in text:
            text = text.replace('<a href="#mentorship">Mentorship</a>', '<a href="#mentorship">Mentorship</a>\n        <a href="/events/">Events</a>')
        home.write_text(refine_home(text))
    print(f'Built {len(students["records"])} supervision and {len(events["records"])} event records.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['build','add-student','add-event','update-student','update-event'])
    parser.add_argument('--record', help='JSON object with fields to add or change; alternatively PROFILE_RECORD environment variable')
    parser.add_argument('--id', help='Existing record ID for an update')
    args = parser.parse_args()
    if args.command != 'build':
        action, kind = args.command.split('-')
        record = json.loads(args.record or os.environ.get('PROFILE_RECORD','{}'))
        print('Saved', change(kind, action, record, args.id))
    build()


if __name__ == '__main__':
    main()

