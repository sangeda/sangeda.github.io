# MUHAS BPharm research catalogue

Initial source: accepted recovered historical records, 21 September 2026.
759 titled projects are included. Two apparent test records and 14 untitled records remain in the internal recovery dataset. Student names, registration numbers, abstracts, legacy file references and internal correction notes are omitted from this initial public version. Supervisor display names and titles retain source wording; whitespace is normalized. No inferred scientific edits or surname-only identity merges are made.

Run **Update BPharm research catalogue** with source `cache` to publish the recovered catalogue. It also runs daily at 05:17 EAT. The Pages deployment restores existing Observatory downloads from their release, without reharvesting OpenAlex.

After Project 224's dictionary and records are installed, set public_catalogue=1 for records to publish (and public_author=1 only to publish student names). Run the workflow manually with source `redcap`. Once verified, set the repository Actions variable BPHARM_SOURCE to `redcap` for subsequent scheduled runs. The secret is REDCAP_PROJECT224_TOKEN. API mode verifies project ID and dictionary, reads only the required fields, and never imports or overwrites REDCap. No raw response is logged or saved. API failures stop deployment and retain the previous site. Zero public flags on an otherwise valid export produces an empty public catalogue, honoring visibility withdrawals.

Search terms and word-cloud frequencies are derived from complete titles and curated keywords. Each project contributes once per term; phrases and their individual words can both appear. Counts describe title vocabulary, not impact or formal topic classification. Supervisor aliases remain for later explicit curation. PDFs and abstracts are not required.

The public JSON cache is refreshed only after a successful API build. Project pages, canonical URLs, JSON-LD and a dedicated sitemap support search discovery. Indexing remains a search-engine decision. The main SEO script links this collection alongside research, leadership, mentorship, publications and DCEPD pages.

## Recovery status versus public release (November 2026)

REDCap Project 224 holds **1,114 records**: 775 legacy rows and 339 newly recovered presentation/proposal records from 2020–2026. Of the newly recovered rows, 334 have a recorded title, five have no title, and none has a confirmed completion year. Every new record was deliberately imported with `curation_status=1` and `public_catalogue=0`. **Do not treat those 339 as published records or automatically change their visibility.**

The public catalogue currently contains **759 searchable titles**. To avoid a page that falsely appears out of date, the REDCap-powered refresh now publishes a **recovery-status summary of aggregate counts only**. It reports all 1,114 source records, the recoveries held for curation, and presentation-year counts (2020–2026). It does *not* publish the held titles, names, registration numbers, source references, internal notes, or unverified completion years.

The `recovery_status` object is computed in memory from REDCap and contains only aggregate numbers. The normal public-project allowlist and author-visibility flags remain unchanged. Later release of reviewed titles requires a separate, explicitly approved REDCap curation/public-visibility step; a scheduled website rebuild alone will never authorize publication.
