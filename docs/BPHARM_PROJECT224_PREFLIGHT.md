# BPharm Project 224 — GitHub read-only preflight

This workflow is separate from the existing public BPharm catalogue refresh and does **not** modify REDCap, the public website, or any other project.

## Use

1. Merge the reviewed pull request that adds this workflow to main.
2. In GitHub, open **Actions → BPharm Project 224 read-only preflight → Run workflow**.
3. Open the run log. The result contains only Project 224 identity/schema checks, live record count, highest BPH ID, and collision count for the proposed 339 IDs (BPH000802–BPH001140).
4. If a secret, API permission, dictionary, or ID check fails, stop and investigate. The script intentionally does not import anything.

The existing repository Actions secret REDCAP_PROJECT224_TOKEN is passed only to this job's environment. Never paste or log its value.

## Important privacy boundary

Do **not** commit the 339-row student-level staging CSV, the legacy REDCap export, staff rosters, registration numbers, private attachments, or the REDCap token to this public repository.

The preflight does not accept a CSV and cannot import records. A future controlled import must receive the CSV through an independently secured, access-restricted handoff. Its import routine must recheck the live ID space immediately before writing, use a five-record test batch, and read back each batch. Keep the recovered collection separate from the MUHAS Publications Observatory, DCEPD, and OSP workflows.

The preflight's output is aggregate operational metadata, not a statement that the 339 student records have been imported.
