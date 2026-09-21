import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from bpharm_indexes import terms,supervisors
class PublicCatalogue(unittest.TestCase):
 def test_public_field_allowlist(self):
  data=json.loads((ROOT/'bpharm-projects/catalogue.json').read_text())
  allowed={'record_id','title','completion_year','supervisor_1','supervisor_2','supervisor_3','supervisor_4','keywords','department','subject_area','student_name'}
  for p in data['records']:
   self.assertLessEqual(set(p),allowed)
   self.assertNotIn(p['record_id'],['BPH000575','BPH000801'])
   self.assertTrue(p['title'])
   self.assertTrue((ROOT/'bpharm-projects/projects'/f'{p["record_id"]}.html').exists())
 def test_full_title_and_supervisors(self):
  self.assertIn('antimicrobial resistance',terms('First sentence. Antimicrobial resistance.'))
  self.assertEqual(terms('malaria malaria').count('malaria'),1)
  self.assertEqual(len(supervisors({'supervisor_1':'Dr. Sangeda','supervisor_4':'Prof. Kaale'})),2)
if __name__=='__main__':unittest.main()
