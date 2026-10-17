# Sprint Notes: M1

Facts below come from the git history and GitHub issues and PRs.

## Sprint info

- **Sprint:** M1 First Vertical Slice
- **Dates:** 2026-09-27 to 2026-10-16 (first and last M1 commits on `main`). 
- **Team members:**

  | Member | GitHub |
  |---|---|
  | Quinn Handy | @QuinnHandy |
  | Asher Nathan | @AsherHelloWorld |
  | Timo Clement | @Timnims |
  | Samuel Mwanduka | @anonymous1194 |

- **Scrum Master / facilitator:** Whole team. 

## Sprint goal

Deliver one complete vertical slice for the Restaurant component: list → search/filter → details → menu → menu items, plus create/update restaurant and add/update menu items, with tests, CI, and documentation.

## Sprint backlog

| Issue # | User story / task | Assignee | Status |
|---|---|---|---|
| #29 | Write the M1 API contract (`docs/api-contract.md`) | Quinn Handy | Done (PR #47) |
| #30 | Add Menu and MenuItem models, menu data, and menu repository | Asher Nathan | Done (PR #48) |
| #31 | Add write support to repositories (save + stable ID generation) | Asher Nathan | Done (PR #50) |
| #32 | As a customer, I want to view a restaurant's details so that I can decide whether to order from it | Quinn Handy | Done (PR #51) |
| #33 | As a customer, I want to search and filter restaurants so that I can find what I'm looking for | Quinn Handy | Done (PR #53) |
| #34 | As a customer, I want to view a restaurant's menu and its items so that I can see what I can order | Quinn Handy | Done (PR #59) |
| #35 | As a restaurant owner, I want to create a restaurant so that customers can find it | Unassigned on GitHub | Done (PR #56 by Timo Clement) |
| #36 | As a restaurant owner, I want to update my restaurant's information so that it stays accurate | Timo Clement | Done (PR #60) |
| #37 | As a restaurant owner, I want to add items to my menu so that customers can order them | Timo Clement | Done (PR #61) |
| #38 | As a restaurant owner, I want to update menu items so that prices and details stay correct | Quinn Handy | Open (no PR yet) |
| #39 | As a customer, I want a simple web page to browse restaurants and view their details | Samuel Mwanduka | Done (PR #52) |
| #40 | As a restaurant owner, I want a form to create or update a restaurant from the web page | Samuel Mwanduka | Done (PR #62) |
| #41 | Tag m1-vertical-slice release and submit the Canvas PDF | Samuel Mwanduka | Open |
| #42 | Prepare and rehearse the M1 live demo | Unassigned on GitHub | Open |
| #43 | Set up GitHub Actions CI to run pytest on PRs | Quinn Handy | Done (PR #49; improved in PR #58 by Timo Clement) |
| #44 | Complete OpenAPI documentation for all M1 endpoints | Quinn Handy | In review (PR #65) |
| #45 | Write the Decision Receipt for our main engineering decision | Unassigned on GitHub | Done (PR #63 by Samuel Mwanduka) |
| #46 | Update README, PROVENANCE, and scrum notes for M1 | Quinn Handy | In review (this PR) |
| #54 | As a customer, I want to search and filter restaurants from the web page so that I can find a restaurant quickly | Samuel Mwanduka | Done (PR #55) |

## Stand-up / meeting log

N/A - communicated all on whatsapp.

## Sprint review

**Completed (closed issues with merged PRs)**
- API contract for all M1 endpoints (#29)
- Data layer: Menu/MenuItem models and menu data (#30), repository writes with atomic saves and stable server-assigned IDs (#31)
- Customer API:
  - restaurant details (#32)
  - search and filter by name and cuisine (#33)
  - restaurant menu (#34)
- Owner API:
  - create restaurant (#35)
  - update restaurant (#36)
  - add menu item (#37)
- Web pages:
  - customer page to browse restaurants (#39)
  - search and filter on the customer page (#54)
  - owner create/update form (#40)
- CI: GitHub Actions runs pytest on every push and PR (#43)
- Decision receipts for our main engineering decisions (#45)

**Demoed:** N/A

**Not finished (open issues)**
- #38: update menu items. `MenuRepository.update_item` and its tests exist, but there is no API route yet.
- #41: tag the `m1-vertical-slice` release and submit the Canvas PDF.
- #42: prepare and rehearse the M1 live demo.
- #44: OpenAPI documentation (PR #65 open, waiting for review).
- #46: README, PROVENANCE, and scrum notes (this PR).

## Retrospective

**What went well**
- whatsapp

**What to improve**
- Not waiting until the last minute, trying to be more proactive

**Action items**


## Contribution summary

Counted from `main` over the M1 period (from 2026-09-27). Commits exclude merge commits. Commit and PR counts show activity, not effort; the percentage column must be agreed by the whole team.

| Member | M1 PRs authored and merged | M1 commits | PRs reviewed and merged for others | Agreed contribution % |
|---|---|---|---|---|
| Quinn Handy | 5: #47, #49, #51, #53, #59 | 9 | 8: #50, #52, #55, #56, #60, #61, #62, #63 | 25% |
| Asher Nathan | 2: #48, #50 | 2 | 3: #47, #49, #51 | 25% |
| Timo Clement | 4: #56, #58, #60, #61 | 5 | 1: #59 | 25% |
| Samuel Mwanduka | 4: #52, #55, #62, #63 | 11 | 2: #48, #53 | 25% |
| **Total** | 15 | 27 | | 100% |

Notes:
- Quinn Handy's 9 commits include `205c552` (a change to `app/static/app.js`), which is part of Samuel Mwanduka's PR #55.
- Timo Clement merged his own PR #58, so it isn't counted as a review.
- Work done outside the repository (for example the Level 1 DFD, meetings, and demo preparation) isn't shown here.
