import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('catalogue', ROOT/'scripts/update_dcepd_catalogue.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class CatalogueTests(unittest.TestCase):
    def row(self, rid='1', listed='Yes', repeat=''):
        return dict.fromkeys(m.FIELDS, '') | {'record_id': rid, 'course_name': 'Example <course>',
            'public_catalogue': listed, 'redcap_repeat_instrument': repeat,
            'private_email': 'PRIVATE_SENTINEL', 'dormant_flag': 'Dormant', 'course_status': 'Under review'}

    def build(self, rows):
        return m.build(rows, 'test', '2026-09-19', {'courses': {}, 'keyword_rules': []})

    def test_exact_inclusion_and_no_extra_eligibility_rules(self):
        result = self.build([self.row(), self.row('2', 'No'), self.row('3', ''), self.row('1', 'Yes', 'course_run_log')])
        self.assertEqual([c['id'] for c in result['courses']], ['1'])
        self.assertNotIn('PRIVATE_SENTINEL', json.dumps(result))

    def test_duplicate_ids_fail(self):
        with self.assertRaises(ValueError): self.build([self.row(), self.row()])

    def test_empty_is_valid_after_successful_export(self):
        self.assertEqual(self.build([])['count'], 0)

    def test_html_escaping_and_official_link(self):
        card = m.render_card(self.build([self.row()])['courses'][0])
        self.assertIn('&lt;course&gt;', card)
        self.assertNotIn('<course>', card)
        self.assertIn(m.APPLY_URL, card)

    def test_metadata_verifies_yes_code(self):
        metadata = [{'field_name': name, 'field_type': 'text'} for name in m.FIELDS]
        next(x for x in metadata if x['field_name'] == 'public_catalogue').update(
            field_type='radio', select_choices_or_calculations='7, Yes | 8, No')
        with patch.dict('os.environ', {'REDCAP_PROJECT75_TOKEN': 'test-only'}), patch.object(m, 'api_export', side_effect=[metadata, []]) as api:
            self.assertEqual(m.fetch_records(), [])
            args = api.call_args.args[2]
            self.assertEqual(args['filterLogic'], "[public_catalogue] = '7'")
            self.assertNotIn('private_email', str(args))

    def test_published_schema(self):
        data = json.loads((ROOT/'dcepd-courses/catalogue.json').read_text())
        self.assertEqual(data['count'], len(data['courses']))
        self.assertEqual(len({c['id'] for c in data['courses']}), data['count'])
        allowed = {'id','title','source_title','code','school','department','fee_tzs','cpd_points','category','tags','apply_url'}
        for course in data['courses']:
            self.assertEqual(set(course), allowed)
            self.assertEqual(course['apply_url'], m.APPLY_URL)

if __name__ == '__main__': unittest.main()
