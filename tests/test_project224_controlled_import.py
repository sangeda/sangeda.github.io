"""Synthetic safety tests. No private data or network access."""
import importlib.util
from pathlib import Path
import unittest
PATH=Path(__file__).resolve().parents[1]/"scripts"/"project224_controlled_import.py"
spec=importlib.util.spec_from_file_location("project224_controlled_import",PATH)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
def synthetic():
    return [{**{f:"" for f in mod.FIELDS},"record_id":f"BPH{i:06d}",
             "student_name":f"Synthetic Student {i}","curation_status":"1",
             "report_status":"0","public_catalogue":"0","public_author":"0",
             "public_abstract":"0","public_report":"0"} for i in range(802,1141)]
def client_for(state,calls):
    def client(content,**kw):
        calls.append((content,kw.get("action")))
        if content=="project":return {"project_id":224}
        if content=="metadata":return [{"field_name":x} for x in mod.FIELDS]
        if content=="record":
            if kw.get("action")=="export":return list(state.values())
            if kw.get("action")=="import":
                import json
                rows=json.loads(kw["data"])
                for row in rows:
                    if row["record_id"] in state:raise AssertionError("Overwrite attempted")
                    state[row["record_id"]]=row
                return {"count":len(rows)}
        raise AssertionError("Unexpected API operation")
    return client
class ImportSafetyTests(unittest.TestCase):
    def test_read_only(self):
        calls=[]
        r=mod.perform(synthetic(),client_for({"BPH000801":{"record_id":"BPH000801"}},calls),"preflight","")
        self.assertEqual(r["records_written"],0)
        self.assertFalse(any(a=="import" for _,a in calls))
    def test_missing_write_confirmation_blocks(self):
        calls=[]
        with self.assertRaises(mod.StopImport):
            mod.perform(synthetic(),client_for({},calls),"first_five","")
        self.assertFalse(calls)
    def test_occupied_id_blocks(self):
        calls=[]
        with self.assertRaises(mod.StopImport):
            mod.perform(synthetic(),client_for({"BPH000802":{"record_id":"BPH000802"}},calls),
                        "first_five",mod.CONFIRMATIONS["first_five"])
        self.assertFalse(any(a=="import" for _,a in calls))
    def test_five_then_remaining(self):
        state={"BPH000801":{"record_id":"BPH000801"}}
        rows=synthetic();calls=[]
        self.assertEqual(mod.perform(rows,client_for(state,calls),"first_five",
                                      mod.CONFIRMATIONS["first_five"])["records_written"],5)
        self.assertEqual(mod.perform(rows,client_for(state,calls),"remaining",
                                      mod.CONFIRMATIONS["remaining"])["records_written"],334)
        self.assertEqual(len(state),340)
    def test_project_mismatch(self):
        with self.assertRaises(mod.StopImport):
            mod.perform(synthetic(),lambda content,**kw:{"project_id":225},"preflight","")
if __name__=="__main__":unittest.main()
