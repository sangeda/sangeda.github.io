import sys, unittest
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_dcepd_dashboard import build, period, F75, F79

def master():
 r=dict.fromkeys(F75,'');r.update(record_id='1',course_name='Course A',course_code='A/2026',course_school_code='School',course_department_code='Department',public_catalogue='No');return r

def run(instance, count='', start='2026-07-01'):
 r=dict.fromkeys(F75,'');r.update(record_id='1',redcap_repeat_instrument='course_run_log',redcap_repeat_instance=str(instance),run_start_date=start,run_participants=count);return r

def app(i, code='A/2026 | Course A'):
 r=dict.fromkeys(F79,'');r.update(record_id=str(i),applied_course_id=code,application_date='2026-07-01',residence_region='Arusha');return r

def make(rows,apps=[]):return build(rows,apps,'2026-09-19T00:00:00+00:00','Test',date(2026,9,19))
class Reporting(unittest.TestCase):
 def test_missing_zero_and_repeat(self):
  p,m=make([master(),run(1),run(2,'0'),run(3,'20')]);d=p['delivery'][0]
  self.assertEqual((d['sessions'],d['reported'],d['unknown'],d['attendance']),(3,2,1,20));self.assertEqual(p['metadata']['listed_courses'],0)
 def test_quarter_boundaries(self):
  self.assertEqual(period(date(2026,6,30)),('2026','2025/26','Q4'));self.assertEqual(period(date(2026,7,1)),('2026','2026/27','Q1'))
 def test_future_and_unknown_dates(self):
  p,_=make([master(),run(1,'2','2026-10-01'),run(2,'2','bad')]);self.assertEqual(p['delivery'][0]['state'],'Future-dated');self.assertEqual(p['delivery'][1]['fy'],'Unknown')
 def test_duplicate_run_rejected(self):
  with self.assertRaises(ValueError):make([master(),run(1),run(1)])
 def test_join_uses_course_code_not_choice_id(self):
  p,m=make([master()],[app(1),app(2,'1')]);self.assertEqual(m['quality']['unmatched_applications'],1);self.assertEqual(m['applications'][0]['course_id'],'1');self.assertIsNone(p['applications'][0]['applications'])
 def test_small_cells_and_identifiers_absent(self):
  a=[app(i) for i in range(5)];a[0]['email']='private@example.test';p,m=make([master()],a)
  self.assertEqual(p['applications'][0]['applications'],5);self.assertNotIn('private@example.test',str(p));self.assertNotIn('record_id',str(p))
 def test_duplicate_app_rejected(self):
  with self.assertRaises(ValueError):make([master()],[app(1),app(1)])
if __name__=='__main__':unittest.main()
