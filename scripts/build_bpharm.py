"""Build public BPharm pages. API reads are allowlisted, in-memory, and read-only."""
import argparse,collections,csv,datetime,html,json,os,re,shutil,sys,urllib.parse,urllib.request
from pathlib import Path
from bpharm_indexes import terms,supervisors,yes
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'bpharm-projects'
BASE='https://sangeda.github.io/bpharm-projects/'
FIELDS=['record_id','title','completion_year','supervisor_1','supervisor_2','supervisor_3','supervisor_4','keywords','department','subject_area']
def clean(value):return re.sub(r'\s+',' ',str(value or '')).strip()
def api(content,**extra):
 token=os.environ.get('REDCAP_PROJECT224_TOKEN','')
 if not token:raise ValueError('Project 224 secret is missing')
 body=urllib.parse.urlencode(dict(token=token,content=content,format='json',returnFormat='json',**extra)).encode()
 req=urllib.request.Request('https://utafiti.muhas.ac.tz/api/',data=body)
 with urllib.request.urlopen(req,timeout=120) as response:return json.load(response)
def refresh():
 project=api('project')
 if not isinstance(project,dict) or str(project.get('project_id'))!='224':raise ValueError('API project identity check failed')
 meta=api('metadata')
 required=set(FIELDS+['public_catalogue','curation_status'])
 if not isinstance(meta,list) or not required <= {r.get('field_name') for r in meta}:raise ValueError('Project 224 dictionary is not ready')
 selected=FIELDS+['public_catalogue','curation_status','public_author','student_name']
 raw=api('record',action='export',type='flat',rawOrLabel='raw',**{f'fields[{i}]':f for i,f in enumerate(selected)})
 if not isinstance(raw,list) or not raw:raise ValueError('No records returned; existing public catalogue preserved')
 rows=[]
 for r in raw:
  if not yes(r.get('public_catalogue')) or str(r.get('curation_status')) in ['1','3'] or r.get('record_id') in ['BPH000575','BPH000801'] or not clean(r.get('title')):continue
  p={k:clean(r.get(k)) for k in FIELDS}
  if yes(r.get('public_author')):p['student_name']=clean(r.get('student_name'))
  rows.append(p)
 return dict(source='REDCap Project 224 public catalogue',as_of=datetime.datetime.now(datetime.timezone.utc).date().isoformat(),records=rows)
def esc(s):return html.escape(str(s),quote=True)
def page(title,description,route,body,structured=None):
 url=BASE+route
 schema=structured or {'@type':'CollectionPage','name':title,'url':url,'description':description}
 schema['@context']='https://schema.org'
 return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><meta name="description" content="{esc(description)}"><link rel="canonical" href="{url}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{url}"><meta property="og:type" content="website"><meta name="twitter:card" content="summary"><link rel="stylesheet" href="/bpharm-projects/style.css"><script type="application/ld+json">{json.dumps(schema,ensure_ascii=False).replace('<',chr(92)+'u003c')}</script></head><body><a class="skip" href="#main">Skip to content</a><header><a href="/">Raphael Z. Sangeda</a><nav><a href="/bpharm-projects/">BPharm research</a><a href="/muhas-publications/">MUHAS Observatory</a><a href="https://muhas-dcepd.github.io/">DCEPD courses</a></nav></header><main id="main">{body}</main><footer>MUHAS BPharm research archive · Recovered historical metadata; corrections are ongoing.</footer></body></html>'''
def build(data):
 rows=data['records'];ids=[r['record_id'] for r in rows]
 if len(set(ids))!=len(ids) or any(not re.fullmatch(r'[A-Za-z0-9_-]+',i) for i in ids):raise ValueError('Invalid or duplicate project IDs')
 cards=[];items=[];years=collections.Counter()
 for p in rows:
  p={k:clean(v) for k,v in p.items() if k in FIELDS+['student_name']}
  sups=supervisors(p);keyword=terms(p['title'],p.get('keywords',''))
  year=p.get('completion_year') or 'Unknown';years[year]+=1
  item=dict(id=p['record_id'],title=p['title'],year=year,supervisors=sups,terms=keyword)
  items.append(item)
  route='projects/'+p['record_id']+'.html';url=BASE+route
  names='; '.join(s['name'] for s in sups) or 'Not recorded'
  body=f'<p class="eyebrow">School of Pharmacy · MUHAS</p><h1>{esc(p["title"])}</h1><p>Completion year: {esc(year)}</p><p>Supervisors: {esc(names)}</p>'
  if p.get('student_name'):body+=f'<p>Student author: {esc(p["student_name"])}</p>'
  body+='<p>Abstract and full report are not available in this version.</p><p><a href="/bpharm-projects/">Back to all projects</a></p>'
  schema={'@type':'CreativeWork','name':p['title'],'url':url,'keywords':keyword,'description':'BPharm student research project metadata from MUHAS.'}
  if year.isdigit():schema['dateCreated']=year
  (OUT/route).write_text(page(p['title']+' | MUHAS BPharm',f'BPharm research project. Year: {year}. Supervisors: {names}.',route,body,schema),encoding='utf-8')
  cards.append(f'<article data-id="{p["record_id"]}"><p class="eyebrow">{esc(year)} · BPharm research</p><h3><a href="{route}">{esc(p["title"])}</a></h3><p>Supervisors: {esc(names)}</p></article>')
 body=f'<p class="eyebrow">Muhimbili University of Health and Allied Sciences</p><h1>BPharm research projects</h1><p class="lead">Explore research from the School of Pharmacy: discover topics, find supervisors and revisit earlier student projects.</p><p class="status">{esc(data["source"])} · Updated {esc(data["as_of"])}. Abstracts and reports will be added as recovered.</p><div class="stats"><div><strong>{len(rows)}</strong> searchable projects</div><div><strong>{len([y for y in years if y!="Unknown"])}</strong> completion years</div></div><section aria-label="Search filters" class="filters"><label>Search titles or keywords<input id="search" type="search" placeholder="e.g. antimicrobial resistance"></label><label>Year<select id="year"><option value="">All years</option></select></label><label>Supervisor<select id="supervisor"><option value="">All supervisors</option></select></label><button id="reset">Reset filters</button></section><p id="count" aria-live="polite">{len(rows)} projects</p><details open><summary>Research terms and annual coverage</summary><p>Term size shows the number of matching projects, not research impact. Click a term to search.</p><div id="cloud" class="cloud"></div><div id="years" class="yearbars"></div></details><h2>Project catalogue</h2><p><a href="catalogue.csv" download>Download public catalogue (CSV)</a></p><div id="projects" class="cards">'+''.join(cards)+'</div><script src="catalogue.js" defer></script>'
 (OUT/'index.html').write_text(page('MUHAS BPharm Research Projects | Search by Year, Supervisor & Topic','Search recovered MUHAS Bachelor of Pharmacy research projects by title, keyword, supervisor and completion year.','',body),encoding='utf-8')
 (OUT/'search.json').write_text(json.dumps(items,ensure_ascii=False),encoding='utf-8')
 with (OUT/'catalogue.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['project_id','title','completion_year','supervisors'])
  for p in items:w.writerow([("'"+str(v)) if str(v).startswith(('=','+','-','@')) else v for v in [p['id'],p['title'],p['year'],'; '.join(s['name'] for s in p['supervisors'])]])
 (OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+BASE+r+'</loc></url>' for r in ['']+['projects/'+i+'.html' for i in ids])+'</urlset>')
 print(f'Built {len(rows)} public project pages')
def main():
 a=argparse.ArgumentParser();a.add_argument('--source',choices=['cache','redcap'],default='cache');args=a.parse_args()
 data=refresh() if args.source=='redcap' else json.loads((OUT/'catalogue.json').read_text())
 # API validation completes before replacing any output. No raw response is saved.
 if (OUT/'projects').exists():shutil.rmtree(OUT/'projects')
 (OUT/'projects').mkdir(parents=True,exist_ok=True)
 build(data)
 if args.source=='redcap':(OUT/'catalogue.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
if __name__=='__main__':
 try:main()
 except Exception:
  print('BPharm build failed. Check secret, server availability and Project 224 dictionary. No raw API response logged.',file=sys.stderr);sys.exit(1)
