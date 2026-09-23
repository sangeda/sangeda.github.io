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
  self.assertIn('Antimicrobial resistance',terms('First sentence. Antimicrobial resistance.'))
  self.assertIn('Sickle cell disease',terms('Sickle cell disease among children'))
  self.assertNotIn('sickle',terms('Sickle cell disease among children'))
  self.assertIn('Dar es Salaam',terms('Community pharmacies in DSM'))
  self.assertNotIn('dsm',terms('Community pharmacies in DSM'))
  self.assertIn('Antiretroviral therapy',terms('Antiretroviral treatment outcomes'))
  self.assertEqual(terms('malaria malaria').count('malaria'),1)
  sups=supervisors({'supervisor_1':'Dr. Sangeda','supervisor_4':'Prof. Kaale'})
  self.assertEqual(len(sups),2)
  self.assertEqual(sups[0]['name'],'Raphael Z. Sangeda')
  self.assertEqual(sups[0]['search_key'],'raphael z sangeda')
  self.assertEqual(supervisors({'supervisor_1':'prof Kennedy Mwambete'})[0]['name'],'Kennedy Mwambete')
if __name__=='__main__':unittest.main()
