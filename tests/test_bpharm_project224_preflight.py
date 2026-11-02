"""Offline tests: no secrets, no network, and no student data."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "scripts" / "bpharm_project224_preflight.py"
spec = importlib.util.spec_from_file_location("bpharm_project224_preflight", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def stub(fields=None, ids=None, project_id=224):
    if fields is None:
        fields = module.REQUIRED_FIELDS
    if ids is None:
        ids = ["BPH000801"]
    def client(content, **options):
        if content == "project":
            return {"project_id": project_id}
        if content == "metadata":
            return [{"field_name": name} for name in fields]
        if content == "record":
            assert options["action"] == "export"
            assert options["fields[0]"] == "record_id"
            return [{"record_id": rid} for rid in ids]
        raise AssertionError("Unknown content")
    return client


class Project224PreflightTests(unittest.TestCase):
    def test_available_range(self):
        result = module.evaluate(stub())
        self.assertTrue(result["id_range_available"])
        self.assertEqual(result["proposed_id_collisions"], 0)
        self.assertEqual(result["highest_bph_numeric_record_id"], 801)
    def test_existing_new_id_is_detected(self):
        result = module.evaluate(stub(ids=["BPH000801", "BPH000802", "BPH001140"]))
        self.assertEqual(result["proposed_id_collisions"], 2)
        self.assertFalse(result["id_range_available"])
    def test_wrong_project_stops(self):
        with self.assertRaises(module.PreflightError):
            module.evaluate(stub(project_id=225))
    def test_missing_schema_stops(self):
        with self.assertRaises(module.PreflightError):
            module.evaluate(stub(fields={"record_id"}))
    def test_duplicate_ids_stop(self):
        with self.assertRaises(module.PreflightError):
            module.evaluate(stub(ids=["BPH000801", "BPH000801"]))


if __name__ == "__main__":
    unittest.main()
