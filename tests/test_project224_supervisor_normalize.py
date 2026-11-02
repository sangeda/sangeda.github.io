"""No real students, secrets or REDCap network: synthetic 1,114-record rehearsal."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

PATH=Path(__file__).resolve().parents[1]/"scripts"/"project224_supervisor_normalize.py"
spec=importlib.util.spec_from_file_location("project224_supervisor_normalize",PATH)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def synthetic_records():
    rows = {f"BPH{i:06d}":{"record_id":f"BPH{i:06d}",
            **{f"supervisor_{j}":"" for j in range(1,5)}}
            for i in range(1,1115)}
    for i in range(1,219):
        rows[f"BPH{i:06d}"]["supervisor_1"] = "DR.NGASSAPA" if i==4 else "NGASSAPA"
    for i in list(range(219,230)) + list(range(1,11)):
        rows[f"BPH{i:06d}"]["supervisor_2"] = "KAALE"
    for i in range(230,238):
        rows[f"BPH{i:06d}"]["supervisor_3"] = "MLOKA"
    for i in range(238,240):
        rows[f"BPH{i:06d}"]["supervisor_4"] = "MINZI"
    return rows

class FakeREDCap:
    def __init__(self,records):
        self.records = records
        self.import_calls=0
    def __call__(self,content,**options):
        if content=="project":
            return {"project_id":224}
        if content=="metadata":
            return [{"field_name":f} for f in mod.FIELDS]
        if content=="record":
            if options.get("action")=="export":
                return [dict(x) for x in self.records.values()]
            if options.get("action")=="import":
                self.import_calls += 1
                rows=json.loads(options["data"])
                for row in rows:
                    assert row["record_id"] in self.records
                    assert len(row)>1
                    for key,value in row.items():
                        if key != "record_id":
                            assert key in mod.FIELDS
                            self.records[row["record_id"]][key]=value
                return {"count":len(rows)}
        raise AssertionError("Unexpected API request")

class SupervisorNormalizationTests(unittest.TestCase):
    def fixture(self):
        client=FakeREDCap(synthetic_records())
        full=mod.change_plan(client.records)
        remaining=mod.change_plan(client.records,exclude_first_five=True)
        self.assertEqual(len(full),249)
        self.assertEqual(len({r[0] for r in full}),239)
        return client,mod.fingerprint(full),mod.fingerprint(remaining)

    def test_exact_plan_hash_and_all_phases(self):
        client,fullsha,restsha=self.fixture()
        with patch.object(mod,"EXPECTED_ALL_SHA",fullsha), patch.object(mod,"EXPECTED_REMAINING_SHA",restsha):
            checked=mod.execute(client,"preflight","")
            self.assertEqual(checked["approved_changes_remaining"],249)
            self.assertEqual(client.import_calls,0)
            first=mod.execute(client,"first_five",mod.CONFIRMATIONS["first_five"])
            self.assertEqual(first["records_written"],5)
            rest=mod.execute(client,"remaining",mod.CONFIRMATIONS["remaining"])
            self.assertEqual(rest["records_written"],234)
            self.assertEqual(rest["field_values_changed"],244)
            self.assertEqual(client.records["BPH000001"]["supervisor_1"],"Olipa Ngassapa")
            self.assertEqual(client.records["BPH000220"]["supervisor_2"],"Eliangiringa Kaale")
            self.assertEqual(client.records["BPH000238"]["supervisor_4"],"Omary Minzi")
            self.assertEqual(len(client.records),1114)

    def test_write_requires_confirmation(self):
        client,fullsha,restsha=self.fixture()
        with self.assertRaises(mod.Stop):
            mod.execute(client,"first_five","")
        self.assertEqual(client.import_calls,0)

    def test_stale_legacy_value_fails_closed(self):
        client,fullsha,restsha=self.fixture()
        client.records["BPH000100"]["supervisor_1"]="Unexpected value"
        with patch.object(mod,"EXPECTED_ALL_SHA",fullsha):
            with self.assertRaises(mod.Stop):
                mod.execute(client,"preflight","")
        self.assertEqual(client.import_calls,0)

    def test_unexpected_record_count_fails(self):
        client,fullsha,restsha=self.fixture()
        del client.records["BPH001114"]
        with self.assertRaises(mod.Stop):
            mod.execute(client,"preflight","")

    def test_sparse_updates_include_no_blank_fields(self):
        client,_,_=self.fixture()
        batch=mod.make_updates(mod.change_plan(client.records))
        self.assertEqual(len(batch),239)
        self.assertTrue(all(set(x).issubset(set(mod.FIELDS)) for x in batch))
        self.assertTrue(all(v for x in batch for k,v in x.items() if k!="record_id"))

if __name__=="__main__":
    unittest.main()
