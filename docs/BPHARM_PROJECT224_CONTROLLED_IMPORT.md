# BPharm Project 224: controlled import from a temporary GitHub Actions secret

A push to main runs **synthetic tests only**, without connecting to REDCap. Live data operations run **only through manual GitHub Actions dispatch**. **Preflight is the default**, writing zero REDCap records.

## Load the private 339-row dataset as a repository secret

The ChatGPT deliverable named **BPharm_Project224_PRIVATE_GitHub_Secret_Value.txt** contains the 339 candidate rows compressed with gzip and encoded with base64. Base64 is NOT encryption: protect the local file as confidential data and never commit it to a public repository. Its 27,684-character value fits GitHub's 48-KB Actions-secret size limit.

1. Open GitHub repository Settings > Secrets and variables > Actions > New repository secret.
2. Name the new secret exactly **BPHARM_PROJECT224_RECOVERY_DATA_GZ_B64**.
3. Open the privately downloaded .txt file, copy its entire single-line content into the secret's Value box, and save.
4. The existing **REDCAP_PROJECT224_TOKEN** remains unchanged.

An alternative is GitHub CLI authenticated on a trusted device:

    gh secret set BPHARM_PROJECT224_RECOVERY_DATA_GZ_B64 --repo sangeda/sangeda.github.io < BPharm_Project224_PRIVATE_GitHub_Secret_Value.txt

## Three manual operations

1. Actions > BPharm Project 224 controlled import > Run workflow. Choose **preflight**, leave confirmation blank. The log reports only aggregate values, verifies the private file SHA-256, Project 224 identity, schema and live ID availability. It does not write.
2. On a successful preflight with zero ID collisions, choose **first_five**, entering exactly **IMPORT PROJECT 224 FIRST FIVE**. This writes BPH000802–BPH000806 and verifies them by REDCap readback.
3. After successful readback, choose **remaining**, entering exactly **IMPORT PROJECT 224 REMAINING**. This writes the other 334 records in batches of 20, rechecking IDs before each batch and verifying by readback.

After all rows are verified, **delete the temporary BPHARM_PROJECT224_RECOVERY_DATA_GZ_B64 repository secret**. Do not delete REDCAP_PROJECT224_TOKEN, which is shared with the public catalogue refresh.

## Safeguards and provenance

- Approved SHA256 of uncompressed CSV: a9fe6dd462975ba005f21dcbdbebf2c3ae528708cde50b7c0c1338bb644d9225.
- Data must contain exactly 339 records, IDs BPH000802–BPH001140, 5 empty titles and 138 missing registration numbers.
- The parser validates 13 field headers, status codes, registration-number format, no duplicate IDs, and private source hash.
- All completion_year fields remain blank, and public_catalogue, public_author, public_abstract and public_report are 0.
- Writes require explicit confirmation, check for target-ID collisions, and verify the imported rows by reading REDCap.
- No automatic retries occur if import counts or readback fail. A partial import requires reconciliation before continuing.
- Only aggregate information is printed in GitHub Actions logs, which are publicly readable for this public repository.
- No student CSV, roster, staff list, or encoded secret value should be added to GitHub version control.

This workflow operates separately from BPharm public catalogue builds and does not alter DCEPD, OSP or MUHAS Observatory workflows.
