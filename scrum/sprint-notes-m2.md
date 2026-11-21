# Sprint Notes: M2

These notes summarize M2 work based on GitHub issues and pull requests. Meeting details and contribution percentages should be confirmed by the team.

## Sprint info

- **Sprint:** M2 Integrated Core System
- **Recorded integration/submission window:** November 18–20, 2026 (confirm formal sprint start date)
- **Team:** Quinn Handy (@QuinnHandy), Asher Nathan (@AsherHelloWorld), Timo Clement (@Timnims), Samuel Mwanduka (@anonymous1194)
- **Scrum Master / facilitator:** Whole team

## Sprint goal

Integrate the M1 restaurant/menu system into a working food delivery application with accounts, authentication, cart, checkout, persistent orders, and a web interface. Add cross-subsystem tests, a regression test, one architectural improvement per member, and documentation for the demo and release.

## Sprint backlog

| Issue(s) | Task | Member | Status |
|---|---|---|---|
| #79–#82 | Users, sign-in/out, roles, and owner authorization | Quinn | Done (PRs #114–#117) |
| #68, #83–#86 | Customer menu and account/profile features | Asher | Done (PRs #118, #120) |
| #87 | Menu update, availability, and deactivation | Samuel | Done (PR #130) |
| #88–#92 | Cart backend and pricing | Asher | Done (PR #121) |
| #93–#96 | Order storage, checkout, and order history | Samuel | Done (PRs #126, #127, #133, #135) |
| #97–#99 | Authentication, cart, checkout, and orders web pages | Asher | Done (PRs #119, #122, #125) |
| #100–#101, #105 | Shared test fixtures, full-flow test, regression test | Timo | Done (PRs #137, #138, #142) |
| #102 | Deactivated-customer integration test | Samuel | Done (PR #136) |
| #103 | Checkout price/availability integration test | Quinn | Done (PR #143) |
| #104 | Cart-rules integration test | Asher | Done (PR #123) |
| #106–#109 | Architectural improvements (one per member) | All | Done (PRs #134, #141, #124, #140) |
| #110 | README, API contract, and OpenAPI tests | Timo | In review (PR #144) |
| #111 | Provenance, sprint notes, and M2 Decision Receipt | Team / Timo | In progress |
| #112–#113 | Release tag, Canvas submission, and live demo | All | Pending verification |

## Stand-up / meeting log

N/A — communicated through WhatsApp and worked together in Labs.

## Sprint review

**Completed:** Sign-in and role-based access, customer profiles, restaurant/menu management, cart and pricing, checkout, order persistence/history, and the integrated web pages. The full workflow and four cross-subsystem scenarios have automated tests. Each member contributed an architectural refactor: dependency providers (#106), domain errors (#107), JSON storage (#108), and shared ordering rules (#109).

**Problems and fixes:** Missing menu-update endpoints were added in #87; an invalid-null PATCH regression was covered in #105. Conflicting PRs for dependency providers and viewing an order were rebuilt. Duplicated ordering checks and inconsistent error responses were consolidated in #109 and #107.

**Still to verify:** Review and merge documentation (#110–#111), complete the M2 Decision Receipt with all four members' in-lab decisions, rehearse the demo, confirm green CI on `main`, and create the `m2-integrated-system` tag for Canvas.

## Retrospective

**What went well:** WhatsApp coordination, parallel development, integration tests, and successful end-to-end functionality.

**What to improve:** Merge dependent branches earlier, update API documentation alongside code, and leave more time for reviews and the demo.

**Action items:** Finish and review documentation, verify every member can demonstrate their work, check CI on `main`, then tag and submit.

## Contribution summary

PR counts below are merged M2 PRs authored, not a measure of effort. Percentages reflect the draft allocation and require team agreement.

| Member | M2 merged PRs | Main contributions | Contribution % (confirm) |
|---|---|---|---|
| Quinn Handy | 6 | Auth, permissions, shared ordering rules, checkout revalidation | 25% |
| Asher Nathan | 8 | Customer/cart features and frontend, JSON store, cart integration test | 25% |
| Timo Clement | 4 (+ #144 in review) | Test fixtures, full-flow test, error refactor, regression test, documentation | 25% |
| Samuel Mwanduka | 7 | Menu changes, checkout/orders, dependency refactor, deactivation test | 25% |
| **Total** | **25 merged PRs** | | **100% (subject to agreement)** |
