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

## Fellows and early-career mentorship — revised November 2026
- **Fatuma Felix Felician**: PI, MUHAS–Sida Small Grants, 2021, gut microbial communities and sickle cell disease severity in children. Original grant application identifies Sangeda as mentor; research mentor explicitly confirmed Sida sponsorship in this conversation.
- **David Thomas Myemba**: PI, RSTMH Early Career Grant, 2024 application about sociocultural HPV vaccination decisions in Tanzanian families. February 2024 support letter confirms Sangeda's supervision. By April 2026, the RSTMH grants manager was approving an extension to submit a final grant report, establishing funded-project administration (not merely an application).
- **Meshack Damian Lugoba**, three programmes: (1) EACoECVS cardiovascular pharmacoepidemiology project, award confirmed by the PI's email of 17 July 2026 and Sangeda's communication of 15 July 2026; (2) MUHAS–Sida Seed Grant (2025/26) genomic repository / ESKAPE pathogens research proposal naming him PI and Sangeda mentor; (3) RSTMH 2023 Early Career Grant application investigating ART loss to follow-up, with a dated support letter and December 2023 funder due-diligence message. The Sida and RSTMH evidence should not be represented as confirmed awards solely on the basis of a proposal/reference.
- **Hamu Joseph Mlyuka**: EDCTP Clinical Research and Product Development Fellow, grant TMA2019IF-2865, starting 1 April 2022 for 21 months, host St Andrews University, supported by official [EDCTP award listing](https://www.edctp.org/clinical-research-and-product-development-fellowships-2019/) and the [EDCTP alumni profile](https://edctpalumninetwork.org/profile/344). July 2022 fellowship-supervision meeting names Raphael Z. Sangeda as home-institution supervisor. Relevant programme included TB clinical-trial design and trial implementation training.
- The public section focuses on **four people and six programme/project associations**. No award-status badges or assumed completion dates are shown. Years refer to documented grant/programme/application years.
- All four are distinct from the record-based **48 BPharm, 3 master's, and 8 PhD supervision** counts, which remain unchanged. Source documents and private emails are not published.
- Funder spelling: **RSTMH** (Royal Society of Tropical Medicine and Hygiene), not “RSMTH”; **EACoECVS** refers to the East African Centre of Excellence for Cardiovascular Sciences programme.
- A separate 2026 MUHAS–Sida proposal identifies Natorias Mgaya Salvatory as junior PI and Sangeda as strategic mentor. That is not included in the current four-person set because its funding/participation stage is only a proposal; it can be considered during a subsequent evidence-based expansion.

## BPharm site refresh
- scripts/bpharm_supervisor_aliases.json is revised to reflect user-confirmed supervisor identities, including Omary Minzi, Eliangiringa Kaale, Olipa Ngassapa, Kennedy Daniel Mwambete, Ambrose Haule and others.
- The existing BPharm publishing workflow can rebuild from REDCap Project 224. It uses a positive public_catalogue filter, excludes review-held curation statuses and empty titles, and emits only allowlisted metadata. It also obeys public_author before displaying student names.
- The 339 recovered records remain non-public pending separate, explicit curation; this change does not alter their REDCap flags.
- The site's BPharm refresh and tests are checked after merge; actual published counts depend on successful GitHub Actions validation.

## Limits
External pages can change or block automated access. This is a targeted audit of profile, site-directory and institutional links, not a guarantee that every outbound publication URL on the website is permanently valid.
