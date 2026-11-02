# MUHAS BPharm research catalogue

Initial source: accepted recovered historical records, 21 September 2026.
759 titled projects are included. Two apparent test records and 14 untitled records remain in the internal recovery dataset. Student names, registration numbers, abstracts, legacy file references and internal correction notes are omitted from this initial public version. Supervisor display names and titles retain source wording; whitespace is normalized. No inferred scientific edits or surname-only identity merges are made.

Run **Update BPharm research catalogue** with source `cache` to publish the recovered catalogue. It also runs daily at 05:17 EAT. The Pages deployment restores existing Observatory downloads from their release, without reharvesting OpenAlex.

After Project 224's dictionary and records are installed, set public_catalogue=1 for records to publish (and public_author=1 only to publish student names). Run the workflow manually with source `redcap`. Once verified, set the repository Actions variable BPHARM_SOURCE to `redcap` for subsequent scheduled runs. The secret is REDCAP_PROJECT224_TOKEN. API mode verifies project ID and dictionary, reads only the required fields, and never imports or overwrites REDCap. No raw response is logged or saved. API failures stop deployment and retain the previous site. Zero public flags on an otherwise valid export produces an empty public catalogue, honoring visibility withdrawals.

Search terms and word-cloud frequencies are derived from complete titles and curated keywords. Each project contributes once per term; phrases and their individual words can both appear. Counts describe title vocabulary, not impact or formal topic classification. Supervisor aliases remain for later explicit curation. PDFs and abstracts are not required.

The public JSON cache is refreshed only after a successful API build. Project pages, canonical URLs, JSON-LD and a dedicated sitemap support search discovery. Indexing remains a search-engine decision. The main SEO script links this collection alongside research, leadership, mentorship, publications and DCEPD pages.

## Recovery and explicit title-only release (November 2026)

Project 224 now holds **1,114 records** (775 legacy and 339 recovered presentation/proposal records from 2020–2026). Exactly **334** of the new rows have titles and five remain untitled. No new completion year has been confirmed.

On **3 November 2026**, the researcher explicitly authorized publishing **334 titles without student names or registration numbers**, labelled by **presentation/proposal year** rather than completion year. The one-time guarded release changed only `public_catalogue=1` for the 334 titled rows, verified after each write batch in REDCap. All 339 rows retain `curation_status=1` (pending), `public_author=0`, `public_abstract=0`, `public_report=0`, and blank `completion_year`; the five untitled rows retain `public_catalogue=0`.

The REDCap-backed public catalogue builder supports this exact approved title-only recovery range (IDs BPH000802–BPH001140), without opening generic pending-curation records. For the 334 titles it extracts only the 2020–2026 year from private `source_refs` and emits a public `presentation_year` field. It never exports the raw source reference, registration number, student name, curation notes or a fabricated completion year. The individual pages, cards, search filters and CSV make the different year meanings explicit. New titles appear **first**, newest presentation year first.

Expected public catalogue count after this update: **1,093** (=759 previously public +334 explicitly authorized titles). The 339-row source recovery stays pending formal curation, and the remaining **five untitled** recovered rows are not searchable. Any later disclosure of student names or reports requires separate approval. Title release is not a statement that research completion or award of a qualification has been verified.

The `recovery_status` object contains only non-identifying aggregate counts, including 1,114 source records, newly released titles, remaining unpublished rows and recorded presentation-year distribution. No private student records are committed to the public GitHub repository.
