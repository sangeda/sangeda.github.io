"""Synthetic validation of user-approved 334-title REDCap visibility release."""
import importlib.util
import json
from pathlib import Path
import unittest

MODULE=Path(__file__).resolve().parents[1]/"scripts"/"project224_release_titles.py"
spec=importlib.util.spec_from_file_location("project224_release_titles", MODULE)
lib=importlib.util.module_from_spec(spec)
spec.loader.exec_module(lib)

def records():
    rows={}
    for n in range(1,1141):
        if 776<=n<=801:
            continue
        rid=f"BPH{n:06d}"
        data=dict(record_id=rid,title="Previously approved project" if n<=775 else "Synthetic recovered title",
            completion_year="2010" if n<=775 else "",
            source_refs="" if n<=775 else "Presentation year 2020",
            curation_status="2" if n<=775 else "1",
            public_catalogue="1" if n<=775 else "0",public_author="0",
            public_abstract="0",public_report="0")
        if n>801:
            years=[]
            for year,qty in lib.EXPECTED_YEARS.items():
                years.extend([year]*qty)
            data["source_refs"]=f"Presentation year {years[n-802]}; synthetic"
        if n>=1136:
            data["title"]=""
        rows[rid]=data
    assert len(rows)==1114
    return rows

class Fake:
    def __init__(self,rows):
        self.rows=rows
        self.writes=[]
    def __call__(self,content,**opts):
        if content=="project":return {"project_id":224}
        if content=="metadata":return [{"field_name":key} for key in lib.FIELDS]
        if content=="record":
            if opts["action"]=="export":
                return [dict(row) for row in self.rows.values()]
            if opts["action"]=="import":
                change=json.loads(opts["data"])
                self.writes.append(change)
                for row in change:
                    assert list(row)==["record_id","public_catalogue"]
                    self.rows[row["record_id"]]["public_catalogue"]=row["public_catalogue"]
                return {"count":len(change)}
        raise AssertionError("Unexpected external call")

class TitleReleaseTests(unittest.TestCase):
    def test_one_field_only_and_334_exact(self):
        fake=Fake(records())
        report=lib.execute(fake,lib.APPROVAL)
        self.assertEqual(report["records_changed"],334)
        self.assertEqual(len(fake.writes),17)
        self.assertEqual(len(fake.rows),1114)
        self.assertEqual(len([r for r in fake.rows.values() if r["public_catalogue"]=="1"]),775+334)
        self.assertEqual(len([r for r in fake.rows.values() if r["curation_status"]=="1"]),339)
        for rid in [f"BPH{n:06d}" for n in range(1136,1141)]:
            self.assertEqual(fake.rows[rid]["public_catalogue"],"0")
        self.assertNotIn("Synthetic recovered title",json.dumps(report))

    def test_authorization_and_unexpected_visibility_fail_closed(self):
        fake=Fake(records())
        with self.assertRaises(lib.Stop):
            lib.execute(fake,"")
        self.assertEqual(fake.writes,[])
        fake.rows["BPH000802"]["public_author"]="1"
        with self.assertRaises(lib.Stop):
            lib.execute(fake,lib.APPROVAL)
        self.assertEqual(fake.writes,[])

    def test_unexpected_recovery_year_or_count_stops(self):
        fake=Fake(records())
        fake.rows["BPH000802"]["source_refs"]="Unknown year"
        with self.assertRaises(lib.Stop):
            lib.execute(fake,lib.APPROVAL)
        fake2=Fake(records())
        del fake2.rows["BPH001140"]
        with self.assertRaises(lib.Stop):
            lib.execute(fake2,lib.APPROVAL)

if __name__=="__main__":
    unittest.main()
