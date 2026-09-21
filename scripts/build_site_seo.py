#!/usr/bin/env python3
"""Idempotent search metadata for static pages and scheduled page rebuilds."""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://sangeda.github.io/'
PAGES = {
    'bpharm-projects/index.html': ('bpharm-projects/', 'MUHAS BPharm Research Projects | Year, Supervisor & Topic', 'Search recovered MUHAS Bachelor of Pharmacy research projects by title, keyword, completion year and supervisor.'),
    'dcepd-dashboard/index.html': ('dcepd-dashboard/', 'MUHAS DCEPD Dashboard | Course Delivery, Attendance & Applications',
        'Explore MUHAS continuing education activity by fiscal year, quarter, school and course. Recorded training attendance and separate application demand from REDCap.'),
    'index.html': ('', 'Prof. Raphael Z. Sangeda | MUHAS Research, Leadership & Mentorship',
        'Academic profile of Prof. Raphael Zozimus Sangeda at MUHAS: research in bioinformatics, HIV and AMR, academic leadership, teaching, mentorship and publications.'),
    'publications.html': ('publications.html', 'Raphael Sangeda Publications & Research Trends | MUHAS',
        'Explore Raphael Z. Sangeda’s indexed publications, research themes and annual trends, with links to ORCID, PubMed and Crossref records.'),
    'muhas-publications/index.html': ('muhas-publications/', 'MUHAS Publications Observatory | Research Output & Collaboration',
        'Explore MUHAS publications using OpenAlex: annual and fiscal-quarter research output, research topics, and downloadable Excel, CSV and SQLite datasets.'),
    'dcepd-courses/index.html': ('dcepd-courses/', 'MUHAS DCEPD Short Courses | Search Catalogue & Apply',
        'Search MUHAS continuing education and professional development courses by subject or school, view course details and apply through the official REDCap system.')}

def optimise_site():
    person = {'@type':'Person','@id':BASE+'#person','name':'Raphael Zozimus Sangeda',
        'alternateName':['Raphael Z. Sangeda','Prof. Raphael Sangeda'], 'honorificPrefix':'Prof.',
        'url':BASE,'jobTitle':'Professor of Pharmaceutical Microbiology and Implementation Research',
        'affiliation':{'@id':BASE+'#muhas'},
        'sameAs':['https://orcid.org/0000-0002-6574-5308',
            'https://scholar.google.com/citations?user=FsMB_1cAAAAJ',
            'https://loop.frontiersin.org/people/652853/overview',
            'https://muhas.ac.tz/user/raphael.zozimus.sangeda/'],
        'knowsAbout':['Bioinformatics','HIV drug resistance','Antimicrobial resistance',
            'Pharmaceutical microbiology','Health informatics','Implementation research']}
    org={'@type':'CollegeOrUniversity','@id':BASE+'#muhas',
         'name':'Muhimbili University of Health and Allied Sciences','alternateName':'MUHAS','url':'https://muhas.ac.tz/'}
    site={'@type':'WebSite','@id':BASE+'#website','url':BASE,'name':'Prof. Raphael Z. Sangeda',
          'publisher':{'@id':BASE+'#person'},'inLanguage':'en'}
    navigation='<!-- SITE-DIRECTORY START --><nav aria-label="Explore this website" style="padding:24px;max-width:1200px;margin:auto;display:flex;flex-wrap:wrap;gap:18px">'+''.join(
        f'<a href="{BASE}{url}">{label}</a>' for url,label in [
            ('','Academic profile'),('#research','Research'),('#leadership','Leadership'),('#mentorship','Mentorship'),
            ('publications.html','Publications and trends'),('muhas-publications/','MUHAS Publications Observatory'),
            ('bpharm-projects/','BPharm research projects'),('dcepd-courses/','MUHAS DCEPD courses'),('dcepd-dashboard/','DCEPD activity dashboard')])+'</nav><!-- SITE-DIRECTORY END -->'
    for path,(route,title,description) in PAGES.items():
        file=ROOT/path
        if not file.exists():continue
        text=file.read_text(encoding='utf-8')
        text=re.sub(r'<!-- SEO START -->.*?<!-- SEO END -->','',text,flags=re.S)
        text=re.sub(r'<title>.*?</title>','',text,flags=re.S|re.I)
        text=re.sub(r'<meta\b(?=[^>]*(?:name|property)=[\"\'](?:description|robots|og:[^\"\']+|twitter:[^\"\']+)[\"\'])[^>]*>','',text,flags=re.I)
        text=re.sub(r'<link\b(?=[^>]*rel=[\"\']canonical[\"\'])[^>]*>','',text,flags=re.I)
        url=BASE+route
        page={'@type':'ProfilePage' if not route else 'CollectionPage','@id':url+'#webpage',
              'url':url,'name':title,'description':description,'isPartOf':{'@id':BASE+'#website'},'inLanguage':'en'}
        graph=[site,person,org,page]
        if not route:
            page['mainEntity']={'@id':BASE+'#person'}
        else:
            graph.append({'@type':'BreadcrumbList','itemListElement':[
                {'@type':'ListItem','position':1,'name':'Home','item':BASE},
                {'@type':'ListItem','position':2,'name':title.split('|')[0].strip(),'item':url}]})
        if route=='dcepd-courses/':
            data=json.loads((ROOT/'dcepd-courses/catalogue.json').read_text())
            page['mainEntity']={'@type':'ItemList','numberOfItems':len(data['courses']),
                'itemListElement':[{'@type':'ListItem','position':i+1,'item':{
                    '@type':'Course','name':c['title'],'courseCode':c['code'],
                    'url':url+'#course-'+c['id'],'provider':{'@id':BASE+'#muhas'}}}
                    for i,c in enumerate(data['courses'])]}
        metadata='\n<!-- SEO START -->\n'+f'<title>{html.escape(title)}</title>\n'
        metadata+=f'<meta name="description" content="{html.escape(description,quote=True)}">\n'
        metadata+=f'<link rel="canonical" href="{url}">\n<meta name="robots" content="index,follow,max-image-preview:large">\n'
        for key,value in [('og:title',title),('og:description',description),('og:url',url),('og:type','website'),('og:site_name','Prof. Raphael Z. Sangeda')]:
            metadata+=f'<meta property="{key}" content="{html.escape(value,quote=True)}">\n'
        metadata+='<meta name="twitter:card" content="summary">\n'
        metadata+='<script type="application/ld+json">'+json.dumps({'@context':'https://schema.org','@graph':graph},ensure_ascii=False).replace('<','\\u003c')+'</script>\n<!-- SEO END -->\n'
        text=text.replace('</head>',metadata+'</head>',1)
        text=re.sub(r'<!-- SITE-DIRECTORY START -->.*?<!-- SITE-DIRECTORY END -->','',text,flags=re.S)
        text=text.replace('</body>',navigation+'\n</body>',1)
        # Crawlable Observatory evidence, also useful when JavaScript is unavailable.
        if route=='muhas-publications/' and (ROOT/'muhas-publications/data/summary.json').exists():
            summary=json.loads((ROOT/'muhas-publications/data/summary.json').read_text())
            rows=''.join(f'<tr><td>{int(r["publication_year"])}</td><td>{int(r["publications"]):,}</td></tr>' for r in summary['annual'])
            evidence='<section class="section" id="annual-publication-record"><h2>MUHAS publication counts by year</h2><p>OpenAlex-indexed works in the current snapshot. Counts remain subject to institutional curation.</p><table><thead><tr><th scope="col">Publication year</th><th scope="col">Works</th></tr></thead><tbody>'+rows+'</tbody></table></section>'
            text=re.sub(r'<!-- SEO-EVIDENCE START -->.*?<!-- SEO-EVIDENCE END -->','',text,flags=re.S)
            text=text.replace('</main>','<!-- SEO-EVIDENCE START -->'+evidence+'<!-- SEO-EVIDENCE END --></main>',1)
        text=re.sub(r'\n{3,}', '\n\n', text)
        file.write_text(text,encoding='utf-8')
    urls=''.join(f'<url><loc>{BASE}{route}</loc></url>' for route,_,_ in PAGES.values())
    (ROOT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+urls+'</urlset>\n')
    (ROOT/'robots.txt').write_text('User-agent: *\nAllow: /\n\nSitemap: '+BASE+'sitemap.xml\nSitemap: '+BASE+'bpharm-projects/sitemap.xml\n')

if __name__=='__main__': optimise_site()

