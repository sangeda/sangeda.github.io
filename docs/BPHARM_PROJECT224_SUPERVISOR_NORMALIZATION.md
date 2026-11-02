# BPharm Project 224: verified supervisor normalization

This is a separate, field-specific update of the **775 historical records**, after successful import of **339 newer projects**. It does not update student details or the public BPharm catalogue.

## Source and controls

- Approved source: BPharm_legacy_supervisor_name_changes_v5.csv, derived from the November 2 REDCap export and user-confirmed identity mapping v5.
- Expected **249 supervisor field substitutions** across **239 legacy records**. Fields: Supervisor 1 = 218, Supervisor 2 = 21, Supervisor 3 = 8, Supervisor 4 = 2.
- The repository stores **70 academic-supervisor spelling/identity aliases**, not student records or the 249 record-specific change rows.
- The code computes a SHA-256 fingerprint of *all* proposed changes from live REDCap and requires it to match the approved offline snapshot. It refuses differences instead of guessing.
- The GitHub Actions push trigger runs a **read-only preflight only**. Writes require manual workflow dispatch and exact confirmation.
- Readback verifies every changed supervisor field and that all other supervisor fields in the affected records remain unchanged.
- Historical original values are preserved in the separately archived local audit CSV. No private student export or data-secret content is committed to this public repository.

## Three-stage process

1. Merge the PR. GitHub automatically runs a **read-only preflight**, checking the live 1,114-record Project 224 state against the 249-field approved snapshot. It prints aggregate counts only.
2. Open **Actions > BPharm Project 224 supervisor normalization > Run workflow**. Choose **first_five** and enter exactly **NORMALIZE PROJECT 224 FIRST FIVE**. This modifies the Supervisor 1 field of BPH000001–BPH000005, verifies each field by readback, and writes nothing else.
3. After the first-five run succeeds, choose **remaining** and enter exactly **NORMALIZE PROJECT 224 REMAINING**. This first confirms the five already updated values and the 244 remaining field substitutions, then updates 234 remaining legacy records in batches of at most 20, with readback after every batch.

Do not run either update operation more than once. If a job fails, stop and inspect before doing anything further; deliberate non-idempotent safety checks prevent accidental replays.

## After normalization

- Verify post-update legacy supervisor identities; do not assume a green GitHub tick proves values without checking the logged readback result.
- The separate BPharm catalogue uses an existing public JSON cache and supervisor alias processing; decide whether to publish a refreshed snapshot only after REDCap curation flags and privacy gates are verified.
- Delete the **temporary student-data** GitHub secret `BPHARM_PROJECT224_RECOVERY_DATA_GZ_B64` after data import, if not already deleted. **Keep** `REDCAP_PROJECT224_TOKEN`, which is needed for authorized REDCap operations.
- Do not change MUHAS Observatory, DCEPD or OSP code for this task.
