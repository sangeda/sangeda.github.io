# MUHAS BPharm research catalogue

Initial source: accepted recovered historical records, 21 September 2026.
759 titled projects are included. Two apparent test records and 14 untitled records remain in the internal recovery dataset. Student names, registration numbers, abstracts, legacy file references and internal correction notes are omitted from this initial public version. Supervisor display names and titles retain source wording; whitespace is normalized. No inferred scientific edits or surname-only identity merges are made.

Run **Update BPharm research catalogue** with source `cache` to publish the recovered catalogue. It also runs daily at 05:17 EAT. The Pages deployment restores existing Observatory downloads from their release, without reharvesting OpenAlex.

After Project 224's dictionary and records are installed, set public_catalogue=1 for records to publish (and public_author=1 only to publish student names). Run the workflow manually with source `redcap`. Once verified, set the repository Actions variable BPHARM_SOURCE to `redcap` for subsequent scheduled runs. The secret is REDCAP_PROJECT224_TOKEN. API mode verifies project ID and dictionary, reads only the required fields, and never imports or overwrites REDCap. No raw response is logged or saved. API failures stop deployment and retain the previous site. Zero public flags on an otherwise valid export produces an empty public catalogue, honoring visibility withdrawals.

Search terms and word-cloud frequencies are derived from complete titles and curated keywords. Each project contributes once per term; phrases and their individual words can both appear. Counts describe title vocabulary, not impact or formal topic classification. Supervisor aliases remain for later explicit curation. PDFs and abstracts are not required.

The public JSON cache is refreshed only after a successful API build. Project pages, canonical URLs, JSON-LD and a dedicated sitemap support search discovery. Indexing remains a search-engine decision. The main SEO script links this collection alongside research, leadership, mentorship, publications and DCEPD pages.
