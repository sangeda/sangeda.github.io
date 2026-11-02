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

## Fellows and early-career mentorship
- Fatuma Felix Felician is documented as PI of a November 2021 MUHAS–Sida Small Grants **application** on gut microbial communities and severity of sickle cell disease among children; Raphael Z. Sangeda is explicitly named mentor in the project document.
- The public entry states **proposal / application**, not awarded fellowship or implemented project, because those statuses have not been independently documented.
- Other named investigators already processed in supervision or fellowship records are not repeated. No private grant documents are linked publicly.

## BPharm site refresh
- scripts/bpharm_supervisor_aliases.json is revised to reflect user-confirmed supervisor identities, including Omary Minzi, Eliangiringa Kaale, Olipa Ngassapa, Kennedy Daniel Mwambete, Ambrose Haule and others.
- The existing BPharm publishing workflow can rebuild from REDCap Project 224. It uses a positive public_catalogue filter, excludes review-held curation statuses and empty titles, and emits only allowlisted metadata. It also obeys public_author before displaying student names.
- The 339 recovered records remain non-public pending separate, explicit curation; this change does not alter their REDCap flags.
- The site's BPharm refresh and tests are checked after merge; actual published counts depend on successful GitHub Actions validation.

## Limits
External pages can change or block automated access. This is a targeted audit of profile, site-directory and institutional links, not a guarantee that every outbound publication URL on the website is permanently valid.
