# Maintaining supervision and academic events

Public pages: https://sangeda.github.io/supervision/ and https://sangeda.github.io/events/.

The authoritative editable lists for these two pages are `data/profile/students.json` and `data/profile/events.json`. These are independent of REDCap Project 224 and the institutional BPharm repository. Do not copy changes into REDCap automatically.

## Commands in chat

Ask the connected assistant, for example:

- **Add event:** [name]; dates [YYYY-MM-DD to YYYY-MM-DD]; city [city]; country [country]; role [role]; sponsor/project [optional]; purpose [optional].
- **Add supervised student:** [name]; degree [BPharm/MSc/MPharm/PhD]; institution [institution]; recorded year [YYYY or Ongoing]; status [Completed/In Progress/Unknown]; research title [title].
- **Update student SUP0001:** status Completed; year [YYYY].
- **Update event EVT0001:** start date [YYYY-MM-DD].

The assistant should inspect the current records, apply only supplied facts, run the builder and checks, commit the change, and verify deployment. This is a maintenance instruction, not a public chatbot or unauthenticated website editing feature.

## GitHub Actions — no local software needed

Open Actions → **Add or update profile record** → Run workflow on main. Choose the command, paste a JSON object in `record`, and provide `record_id` only for an update. The workflow validates, commits, rebuilds the pages and sitemap, and deploys the complete site. It uses GitHub's existing workflow token; no REDCap token is needed.

Event example (replace placeholders before running):

```json
{"name":"Event title","start_date":"2027-01-27","end_date":"","city":"Dar es Salaam","country":"Tanzania","role":"Presenter","sponsor":"","description":"Purpose or contribution"}
```

Student example:

```json
{"name":"Student name","level":"MPharm","institution":"Muhimbili University of Health and Allied Sciences","year":"Ongoing","status":"In Progress","title":"Research title"}
```

Update example with command `update-student` and the relevant `record_id`:

```json
{"status":"Completed","year":"2027"}
```

Only public academic information belongs in these files. Do not add contacts, registration numbers, assessments or private notes. Missing optional fields can be blank. Never invent a date, role, institution, degree or completion status. Exact duplicate additions are rejected. Similar records require human review; IDs remain stable when edited.

## Local command line

```bash
python scripts/profile_records.py add-event --record '{"name":"Event title","start_date":"2027-01-27","country":"Tanzania","role":"Presenter"}'
python scripts/profile_records.py update-student --id SUP0001 --record '{"status":"Completed","year":"2027"}'
python scripts/build_site_seo.py
python -m unittest discover -s tests -p 'test_profile_records.py'
```

Commit the source JSON and generated `supervision/`, `events/`, homepage and sitemap changes. The main-branch deployment also rebuilds these pages. The website filters are read-only, shareable through their URL, and export only matching records to CSV. All records are in the HTML for search engines and visitors without JavaScript.

## Initial import decisions — 31 October 2026

- 59 supervision records: 48 BPharm, 3 MSc, 8 PhD. These are **records**, not 59 verified unique students. Five PhD entries say In Progress in the supplied file; this is not a newly verified status.
- 93 activity records; four lack dates. Dates were read as day/month/year and stored as ISO dates. No year was inferred from an event title.
- Preserve source degree labels: the file says MSc, although MPharm was mentioned in the request. The command and filters support both.
- Whitespace was normalized; spelling and research titles were retained. No uncertain merges or changes to degree/year/status were made.
- Potential review items include Kelvin Kasu (same title, 2019/2020); Lusajo Shitindi / Shitindi Lusajo; Poyongo Baraka / Baraka P Poyongo; Hafidh/Hafidhi Hamim; Deus Mtweve / Deus M. Mtweve; and George Nyamanda Musiba listed at MSc and BPharm levels for a similar project. A person appearing at multiple levels is not automatically a duplicate.
- UbuntuNet 2016 and H3ABioNet 2019 have related event names with different dates. Retain until confirmed, rather than silently picking a date.
- “Recorded year” is used because the CSV does not establish whether every year means graduation, project completion or publication. Events include academic service and supervision visits as well as conferences.
