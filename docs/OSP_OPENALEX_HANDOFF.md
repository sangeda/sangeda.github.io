# OSP and OpenAlex — integration handoff

User context recorded 31 October 2026. No REDCap records were accessed or imported for this homepage change.

- Public opportunities portal: https://muhas-osp.github.io/opportunities/
- Related REDCap projects at utafiti.muhas.ac.tz: **247** and **248**. Confirm each project's role, schema and joining identifiers before integrating.
- The user reports **1,364 records** in a mixed register including academic, administrative and honorary members, one-off students and publishers. This is not a verified count of academic staff or OpenAlex authors.
- Planned use: cooperate with the OpenAlex Observatory on identity matching and institutional curation. Keep the opportunities catalogue, person register and publication corpus as distinct datasets.
- First classify record types, retain source IDs, normalize names and aliases, collect available ORCID/OpenAlex IDs, and review uncertain matches. Do not match by name alone or silently treat every registry record as current academic staff.
- School/department attribution should preserve evidence, effective dates and curation decisions. Keep private contacts and API credentials out of public exports.
- The current OpenAlex harvest returned HTTP 401 Unauthorized. Connecting this register does not resolve API authentication; handle that separately before the next institutional harvest.

Homepage change: link to the public OSP portal only. No authenticated REDCap administration or data-entry URLs are exposed in the homepage navigation, and no change to either REDCap project is authorized by this handoff alone.
