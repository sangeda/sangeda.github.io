# Profile links, Fellows and BPharm refresh — verification notes (3 November 2026)

## Academic profiles added or retained
- ORCID: https://orcid.org/0000-0002-6574-5308 (retained; ORCID SPA requires JavaScript to inspect linked-websites sidebar)
- Google Scholar: https://scholar.google.com/citations?user=FsMB_1cAAAAJ (retained)
- Frontiers Loop: https://loop.frontiersin.org/people/652853/overview (retained)
- MUHAS: https://muhas.ac.tz/user/raphael.zozimus.sangeda/ (retained)
- LinkedIn: https://tz.linkedin.com/in/sangeda (added, identified as Raphael Zozimus Sangeda)
- ResearchGate: https://www.researchgate.net/profile/Raphael-Sangeda (added, verified MUHAS-affiliated Raphael Z. Sangeda profile)
- Cureus: https://www.cureus.com/users/253652-raphael-z-sangeda (added, Raphael Z. Sangeda profile)

These display as seven accessible, differently colored, oval badges at the top of the academic homepage. The sameAs identity list is also maintained in scripts/build_site_seo.py for rebuilds.

## Site navigation preservation
- Homepage /, publications.html, /supervision/, /events/, /bpharm-projects/ and /muhas-publications/ are repository-backed paths.
- The DCEPD link remains https://muhas-dcepd.github.io/.
- The OSP opportunities link remains https://muhas-osp.github.io/opportunities/. Independent crawler access to OSP could not be confirmed; the existing link is retained rather than guessed or replaced.
- No source files under the MUHAS Publications Observatory, DCEPD or OSP are changed.

## Fellows and early-career mentorship — corrected 3 November 2026

There are **seven investigators and nine distinct programme/project entries**. These are *not* nine awarded grants; some records are application documents. None is automatically a degree-supervision record. User-provided concept notes and project title pages are the principal source for the 2020 SPARCO and 2022 Sida corrections; confidential source documents are not linked from the public site.

1. **Fatuma Felix Felician** — MUHAS–Sida Small Grants, 2021. PI, childhood sickle-cell disease gut microbial communities project. Raphael Z. Sangeda: mentor. User confirmed Sida sponsorship.
2. **David Thomas Myemba** — RSTMH Early Career Grant, 2024, sociocultural HPV vaccination decision-making in Tanzanian families. His February 2024 recommendation letter identifies Sangeda as project supervisor; subsequent RSTMH correspondence about his final report supports that this became an administered grant.
3. **Meshack Damian Lugoba** — three distinct records:
   - **MUHAS–Sida, 2022** — *Uptake of Viral Load Testing and the Role of Pharmacy Refill Adherence to Predict Antiretroviral Therapy Outcome among Adolescents and Adults in Tanzania*. PI Meshack Lugoba; co-investigator Ritah Francis Mutagonda; mentor Raphael Zozimus Sangeda. The user corrected the earlier site entry: **the 2026 Sida ESKAPE proposal was not awarded and must not be presented as his Sida-funded award**.
   - **RSTMH, 2023** — *Predictors of the Observed High Prevalence of Loss to Follow-Up among Adolescents and Adults on Antiretroviral Therapy in Tanzania*. Early Career Grants Programme **application** supported by a dated recommendation letter and RSTMH due-diligence correspondence; award not independently asserted.
   - **EACoECVS, proposal dated December 2025; award confirmed July 2026** — *Pharmacoepidemiology of Cardiovascular Medicines Across Tertiary and Primary Health Care Facilities in Tanzania: Bridging Evidence Gaps to Strengthen CVD Prevention and Continuity of Care*. PIs Meshack Lugoba and Hillary Mshana; supervisor Raphael Z. Sangeda; co-supervisor Naizihijwa Majani (JKCI). Collaborators include MUHAS Schools of Pharmacy/Clinical Medicine, JKCI and selected PHC facilities. PI's 17 July 2026 grant-award communication verifies the award.
4. **Hamu Joseph Mlyuka** — EDCTP Clinical Research and Product Development Fellowship, grant TMA2019IF-2865 (2022). University of St Andrews/PanACEA clinical-trial training. Fellowship supervision minutes (July 2022) name Sangeda as home-institution supervisor.
5. **Daniel Kandonga** — **SPARCO–NIH Small Grants, 2020**, PI: *Automating Migration of Consistent Sickle Cell Disease Clinical-Database at Muhimbili National Hospital in Tanzania*. Co-investigators Upendo Masamu (statistician), Frank Makundi (IT specialist) and Jesca Ondego (data clerk). Mentor Dr Raphael Sangeda, then Senior Lecturer and MUHAS Sickle Cell Programme Data Manager.
6. **Ritah Mutagonda** — **SPARCO–NIH 2020/2021 fellowship concept note**: *Streptococcal pneumoniae Carriage, Serotypes and Antibiotic Resistance Profile among Children with Sickle Cell Disease Who Are Using Pneumococcal Prophylaxis in Tanzania*. The scientific name wording follows the user-supplied concept title verbatim. The concept-note record does not by itself establish an award or completion.
7. **Upendo Masamu** — **SPARCO–NIH Small Grants, 2020**, PI: *Upgrading Biorepository to Support Genomics and Clinical Research: A Practical Approach from Sickle Cell Disease Programme at Muhimbili National Hospital*. Co-investigators Daniel Kandonga and Josephine Mgaya. Mentor Dr Raphael Sangeda.

The public section retains person-based cards with sponsor ovals and project descriptions, avoids unnecessary status badges, and does not link to private applications or expose unpublished source documents. Counts remain **48 BPharm, 3 master's and 8 PhD supervision records**.

Funder spelling: **RSTMH** (Royal Society of Tropical Medicine and Hygiene), **EACoECVS**, **SPARCO–NIH**, **MUHAS–Sida**, **EDCTP**. An unrelated 2026 MUHAS–Sida proposal naming Natorias Mgaya Salvatory as PI is not included in the present seven-person update.

## BPharm site refresh
- scripts/bpharm_supervisor_aliases.json is revised to reflect user-confirmed supervisor identities, including Omary Minzi, Eliangiringa Kaale, Olipa Ngassapa, Kennedy Daniel Mwambete, Ambrose Haule and others.
- The existing BPharm publishing workflow can rebuild from REDCap Project 224. It uses a positive public_catalogue filter, excludes review-held curation statuses and empty titles, and emits only allowlisted metadata. It also obeys public_author before displaying student names.
- The 339 recovered records remain non-public pending separate, explicit curation; this change does not alter their REDCap flags.
- The site's BPharm refresh and tests are checked after merge; actual published counts depend on successful GitHub Actions validation.

## Limits
External pages can change or block automated access. This is a targeted audit of profile, site-directory and institutional links, not a guarantee that every outbound publication URL on the website is permanently valid.
