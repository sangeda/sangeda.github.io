import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import profile_records as p


class ProfileTests(unittest.TestCase):
    def fixture(self, root):
        folder = root/'data/profile'
        folder.mkdir(parents=True)
        for kind in ['student', 'event']:
            (folder/(p.FILES[kind]+'.json')).write_text(json.dumps({'updated_at':'2026-10-31','records':[]}))

    def test_invalid_dates_and_fields(self):
        for row in [dict(name='X', start_date='2026-02-30'),dict(name='X',start_date='2026-05-02',end_date='2026-05-01'),dict(name='X',secret='bad')]:
            with self.assertRaises(ValueError): p.validate('event', row)

    def test_add_update_duplicate_and_failed_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            row=dict(name='A',level='MPharm',status='In Progress',year='Ongoing')
            ident=p.change('student','add',row,root=root)
            self.assertEqual(ident,'SUP0001')
            with self.assertRaises(ValueError):p.change('student','add',row,root=root)
            p.change('student','update',{'status':'Completed','year':'2027'},ident,root)
            self.assertEqual(p.load('student',root)['records'][0]['year'],'2027')
            before=(root/'data/profile/students.json').read_bytes()
            with self.assertRaises(ValueError):p.change('student','update',{'year':'bad'},ident,root)
            self.assertEqual(before,(root/'data/profile/students.json').read_bytes())

    def test_escaping_unknown_dates_and_static_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            p.change('event','add',{'name':'</script><script>alert(1)</script>','role':'Participant'},root=root)
            p.build(root)
            text=(root/'events/index.html').read_text()
            self.assertNotIn('</script><script>alert(1)',text)
            self.assertIn('&lt;script&gt;',text)
            self.assertIn('Date not recorded',text)
            self.assertIn('id="EVT0001"',text)

    def test_fellow_cards_and_grant_programmes(self):
        homepage = (Path(__file__).resolve().parents[1] / 'index.html').read_text(encoding='utf-8')
        section = homepage.split('<section id="fellows"', 1)[1].split('<section id="opportunities"', 1)[0]
        self.assertEqual(section.count('class="fellow-record"'), 9)
        self.assertEqual(section.count('class="fellow-grant"'), 11)
        self.assertEqual(section.count('<a class="funder-pill '), 11)
        self.assertNotIn('<span class="funder-pill ', section)
        for url in (
            'https://sida.se/en',
            'https://www.sickleinafrica.org/',
            'https://ucghi.universityofcalifornia.edu/fellowships/glocal-health-fellowship/',
            'https://www.rstmh.org/grants',
            'https://eacecs.or.tz/',
            'https://www.edctp.org/clinical-research-and-product-development-fellowships-2019/',
        ):
            self.assertIn('href="'+url+'"', section)

        for name in (
            'Fatuma Felix Felician',
            'David Thomas Myemba',
            'Meshack Damian Lugoba',
            'Hamu Joseph Mlyuka',
            'Daniel Kandonga',
            'Ritah Mutagonda',
            'Upendo Masamu',
            'Hafidhi Hussein Ntissi',
            'Liberata Alexander Mwita',
        ):
            self.assertIn(name, section)
        for funder in ('funder-sida', 'funder-rstmh', 'funder-eac', 'funder-edctp', 'funder-sparco', 'funder-glocal'):
            self.assertIn(funder, section)
        self.assertEqual(section.count('SPARCO–NIH Small Grants'), 3)
        self.assertIn('TMA2019IF-2865', section)
        self.assertIn('Point Prevalence Survey and Pattern of Antimicrobial Use at Muhimbili National Hospital', section)
        self.assertIn('MUHAS–Sida Antimicrobial Stewardship Grant', section)
        self.assertIn('Identification of Genetic Markers Associated with Anemia in Individuals Affected with Sickle Cell Disease', section)
        self.assertIn('UCGHI GloCal Health Fellowship', section)
        self.assertIn('2019–2020', section)
        self.assertIn('Automating Migration of Consistent Sickle Cell Disease Clinical-Database', section)
        self.assertIn('Upgrading Biorepository to Support Genomics and Clinical Research', section)
        self.assertIn('Streptococcal pneumoniae', section)
        self.assertIn('Uptake of Viral Load Testing and the Role of Pharmacy Refill Adherence', section)
        self.assertIn('co-investigator: Ritah Francis Mutagonda', section)
        self.assertIn('Hillary Mshana', section)
        self.assertIn('Naizihijwa Majani', section)
        self.assertIn('grant awarded in 2026', section)
        self.assertNotIn('Leveraging Global Genomic Repositories', section)
        self.assertIn('2022</time>', section)
        self.assertIn('2023 grant application', section)
        self.assertIn('not counted as an additional degree supervised', section)
        self.assertNotIn('class="fellow-status"', section)
        self.assertNotIn('href="https://drive.google.com/', section)
        for count in ('48', '3', '8'):
            self.assertIn('<strong>'+count+'</strong>', homepage)

    def test_real_source_ids(self):
        for kind in ['student','event']:
            data=p.load(kind)
            self.assertGreater(len(data['records']),0)


if __name__=='__main__':unittest.main()
