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

    def test_real_source_ids(self):
        for kind in ['student','event']:
            data=p.load(kind)
            self.assertGreater(len(data['records']),0)


if __name__=='__main__':unittest.main()
