# DCEPD course catalogue

Only Project 75 master records whose `public_catalogue` label is Yes are included.
No dormancy, accreditation, date or application-system rule is applied here.
Initial public outputs were built from the supplied 19 September 2026 labelled export.
The source date remains visible until a successful API refresh replaces it.

## Activate API refresh

In repository Settings > Secrets and variables > Actions, add
`REDCAP_PROJECT75_TOKEN` with the Project 75 API token. Prefer an export-only
token/account with access to metadata and the course registry. Never paste it
into source code, an issue, a workflow file or a chat message.

Run **Update DCEPD course catalogue**, keeping `refresh_api` checked.
To deploy the existing supplied snapshot before adding the token, uncheck it.
The scheduled refresh runs daily at 04:37 East Africa Time. Failure preserves
the existing public page and its last successful source timestamp.

The exporter verifies the stored Yes code against metadata, requests only
eight course fields and publishes an explicit public schema. It never queries
Project 79, writes to REDCap, exports contacts or publishes raw registry files.

`scripts/dcepd_taxonomy.json` contains proposed title-based categories and tags
keyed by registry ID and bound to the original title. Changed or new titles
fall back to Other courses until classified, while remaining listed. Original
titles and historical codes remain intact. Minor display spelling corrections
are editorial only. No eligibility, accreditation or intake claims are inferred.

Every Apply button opens the official general application survey. Applicants
must select their course there. Preselection awaits the separate mapping work.

The deployment restores Observatory downloads from its latest published release,
verifies available checksums and database integrity, and regenerates its display
from the archived works without changing retrieval timestamps. It shares the
Observatory workflow concurrency group to avoid simultaneous site deployments.

Run tests: `python -m unittest discover -s tests -p 'test_dcepd_catalogue.py'`.
