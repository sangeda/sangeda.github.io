# DCEPD dashboard contract

Project 75 owns course records and repeating `course_run_log` records. Project 79 owns application records. The dashboard exports selected fields read-only, never imports, and does not enforce source-system rules.

Secrets: `REDCAP_PROJECT75_TOKEN` and `REDCAP_PROJECT79_TOKEN`. The existing daily DCEPD workflow refreshes both source feeds and publishes aggregates only. Failed exports or schema validation stop publication and preserve the last deployed version. Tokens, raw API responses and application records must never be logged, committed, uploaded as public workflow artifacts, or staged for Pages.

Course catalogue inclusion remains `public_catalogue=Yes` on master records. Activity statistics include historical/non-catalogue courses. Each repeating Run is one session. Participants are recorded attendances, not unique people or certificates. Missing/invalid attendance remains unknown, explicit zero remains zero. Fiscal years begin July; sessions use start date and applications use application date. Future-dated Runs are separate.

## Cross-project handoff

The supplied Project 79 codebook has `applied_course_id` as the course selection field, and `course_code` as a descriptive display field. The reporting join extracts the code from the labelled selection and requires a unique exact Project 75 `course_code`. It does not assume a Project 79 choice number equals the Project 75 record ID. Unmatched or duplicate codes remain unmatched. The other workstream should provide an authoritative crosswalk or synchronised lookup for historical code changes; the dashboard must not guess or rewrite them.

No applicant statuses are interpreted as attendance/completion. No conversion rate is computed without a verified intake/Run linkage. Changes to selection fields or lookup labels need corresponding read-only mapping updates and tests here.

## Public vs management

Public: aggregate course-period delivery rows and application counts, aggregate geographic reach. Application cells below five are withheld, so filtered sums may be lower bounds. Geographic summaries cover the full snapshot and deliberately do not cross-filter with course/intake; small groups combine. No applicant identifiers, contact details, free text or finances are exported. Geography currently uses labelled ranked tables; a map requires verified boundaries and coverage checks.

Management: local standalone HTML generated only with `--management-output /absolute/path/outside/repository.html`. Contains exact aggregate demand and quality checks, no applicant identities. It is not uploaded by the public workflow. Hosting a live management dashboard requires a private repository/runner and authenticated institutional hosting; GitHub Pages is not that access boundary. No client-side password workaround.

## Downloads and refresh

Public filters: calendar year, July-based fiscal year, quarter, school, department, course. CSV exports include source timestamp. The existing historical-course XLSX remains a separately dated catalogue download. Management reviews built from supplied files remain fixed snapshots and are not represented as live.

Run local tests: `python -m unittest discover -s tests -p 'test_dcepd*.py'`.
