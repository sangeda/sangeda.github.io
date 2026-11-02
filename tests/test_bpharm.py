import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from bpharm_indexes import terms,supervisors
from build_bpharm import recovery_status,build
import tempfile
from unittest.mock import patch
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
  self.assertEqual(supervisors({'supervisor_1':'prof Kennedy Mwambete'})[0]['name'],'Kennedy Daniel Mwambete')

class RecoveryStatusTests(unittest.TestCase):
 def test_held_student_data_never_serialized(self):
  live=[
   {'record_id':'BPH000001','title':'Public entry','source_refs':'', 'public_catalogue':'1','curation_status':'2'},
   {'record_id':'BPH000802','title':'Private sample title','student_name':'Private sample student','regno':'2020-01-00001','source_refs':'Presentation year 2020; report presentation','public_catalogue':'0','curation_status':'1'},
   {'record_id':'BPH000803','title':'','student_name':'Private sample student 2','source_refs':'Presentation year 2026; proposal','public_catalogue':'0','curation_status':'1'},
  ]
  summary=recovery_status(live)
  self.assertEqual(summary['redcap_record_count'],3)
  self.assertEqual(summary['recovered_record_count'],2)
  self.assertEqual(summary['recovered_title_count'],1)
  self.assertEqual(summary['recovered_untitled_count'],1)
  self.assertEqual(summary['recovered_held_count'],2)
  self.assertEqual(summary['presentation_year_counts']['2020'],1)
  self.assertEqual(summary['presentation_year_counts']['2026'],1)
  self.assertNotIn('Private sample',json.dumps(summary))
  self.assertNotIn('2020-01-00001',json.dumps(summary))
  with tempfile.TemporaryDirectory() as tmp:
   folder=Path(tmp)
   (folder/'projects').mkdir()
   public={'source':'REDCap Project 224 public catalogue','as_of':'2026-11-03',
           'records':[{'record_id':'BPH000001','title':'Public entry','completion_year':'2010',
                      'supervisor_1':'Olipa Ngassapa'}], 'recovery_status':summary}
   with patch('build_bpharm.OUT',folder):
    build(public)
   page=(folder/'index.html').read_text()
   self.assertIn('3',page)
   self.assertIn('2020–2026',page)
   self.assertIn('Public entry',page)
   self.assertIn('awaiting curation and release',page)
   self.assertNotIn('Private sample',page)
   self.assertNotIn('2020-01-00001',page)

if __name__=='__main__':unittest.main()
