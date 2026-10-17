# Provenance Record

> Labels follow our best reading of the course guide; update them if the M1 Canvas page names different ones.

This file records where every consequential piece of work in this repository came from: code, tests, diagrams, design decisions, and documentation. Each row names the team member responsible for the artifact. By being listed, that member confirms they can explain, test, and defend the work.

## Labels

| Label | Meaning |
|---|---|
| **HUMAN** | Written by the team without AI or external help |
| **AI-ASSISTED** | AI suggested or drafted parts; a team member substantially edited, verified and tested it |
| **AI-GENERATED** | Mostly produced by AI; a team member reviewed, tested and can explain it |
| **EXTERNAL** | Adapted from documentation, tutorials or other outside sources (cite the URL) |

## Record

Dates are the day the PR was merged into `main` (Pacific time, from GitHub). Members are the PR authors. "Reviewed and merged by" is taken from the PR history. Label, Tool/source and "What was assisted" can only be filled in by the member responsible.

| Date | Artifact (file/feature) | Commit or PR | Label | Tool/source | Member responsible | What was assisted | How it was verified (tests, review, manual check) |
|---|---|---|---|---|---|---|---|
| 2026-09-24 | FastAPI app setup and `Restaurant` model (`app/main.py`, `app/schemas/restaurant.py`) | PR #4, PR #5 | TODO (member to confirm) | TODO (member to confirm) | Timo Clement | TODO (member to confirm) | Reviewed and merged by Quinn Handy; covered by `tests/test_health.py` and `tests/test_restaurant.py` |
| 2026-09-24 | Restaurant route → service → repository layers, config, and `data/restaurants.json` | PR #7 (`98d75ab`), PR #13 (`506f88e`) | TODO (member to confirm) | TODO (member to confirm) | Quinn Handy | TODO (member to confirm) | PR #7 reviewed and merged by Asher Nathan, PR #13 by Timo Clement; covered by `tests/test_restaurant.py` and `tests/test_restaurant_repository.py` |
| 2026-09-25 | Tests for `/health` and `/restaurants` (`tests/test_health.py`, `tests/test_restaurant.py`) | PR #14 (`8e8e92c`) | TODO (member to confirm) | TODO (member to confirm) | Samuel Mwanduka | TODO (member to confirm) | Reviewed and merged by Asher Nathan; tests pass in the full suite |
| 2026-09-25 | Repository tests (`tests/test_restaurant_repository.py`) | PR #17 (`4c7b4db`) | TODO (member to confirm) | TODO (member to confirm) | Timo Clement | TODO (member to confirm) | Reviewed and merged by Samuel Mwanduka; tests pass in the full suite |
| 2026-10-02 | M1 API contract (`docs/api-contract.md`) | PR #47 (`d876183`); search parameters updated in PR #53 | TODO (member to confirm) | TODO (member to confirm) | Quinn Handy | TODO (member to confirm) | Reviewed and merged by Asher Nathan; TODO: note any check against the implementation |
| 2026-10-09 | Menu and MenuItem models, `data/menus.json`, and menu repository (#30) | PR #48 (`61fe242`) | TODO (member to confirm) | TODO (member to confirm) | Asher Nathan | TODO (member to confirm) | Reviewed and merged by Samuel Mwanduka; `tests/test_menu_repository.py` |
| 2026-10-09 | CI workflow (`.github/workflows/tests.yml`) (#43) | PR #49 (`398e6e5`, `3e86f4c`, `6f2d976`, `8ed326e`) | TODO (member to confirm) | TODO (member to confirm) | Quinn Handy | TODO (member to confirm) | Reviewed and merged by Asher Nathan; a deliberately failing test (`6f2d976`) confirmed CI fails, then was removed (`8ed326e`) |
| 2026-10-12 | Repository write support: saving, atomic writes, stable IDs (#31) | PR #50 (`f794809`) | TODO (member to confirm) | TODO (member to confirm) | Asher Nathan | TODO (member to confirm) | Reviewed and merged by Quinn Handy; `tests/test_restaurant_repository_write.py`, `tests/test_menu_repository_write.py` |
| 2026-10-14 | Restaurant details endpoint `GET /restaurants/{restaurant_id}` (#32) | PR #51 (`ea5fd43`) | TODO (member to confirm) | TODO (member to confirm) | Quinn Handy | TODO (member to confirm) | Reviewed and merged by Asher Nathan; `tests/test_restaurant_details.py` |
| 2026-10-15 | Customer web page (`app/static/index.html`, `app/static/app.js`, `app/static/api.js`) (#39) | PR #52 (`3d4c05d`, `b793a50`, `e297fef`) | TODO (member to confirm) | TODO (member to confirm) | Samuel Mwanduka | TODO (member to confirm) | Reviewed and merged by Quinn Handy; `tests/test_frontend.py` |
| 2026-10-15 | Search and filter on `GET /restaurants` (#33) | PR #53 (`dbcc187`) | TODO (member to confirm) | TODO (member to confirm) | Quinn Handy | TODO (member to confirm) | Reviewed and merged by Samuel Mwanduka; `tests/test_restaurant_search.py` |
| 2026-10-15 | Web page search and cuisine filter (#54) | PR #55 (`3c4b9c9`, `3d1bb2d`, `5124249`; `205c552` by Quinn Handy) | TODO (member to confirm) | TODO (member to confirm) | Samuel Mwanduka | TODO (member to confirm) | Reviewed and merged by Quinn Handy; `tests/test_frontend.py` |
| 2026-10-16 | Create restaurant endpoint `POST /restaurants` (#35) | PR #56 (`570dd15`) | TODO (member to confirm) | TODO (member to confirm) | Timo Clement | TODO (member to confirm) | Reviewed and merged by Quinn Handy; `tests/test_create_restaurant.py` |
| 2026-10-16 | CI workflow improvements (`.github/workflows/tests.yml`) | PR #58 (`7253fdd`, `a00475a`) | TODO (member to confirm) | TODO (member to confirm) | Timo Clement | TODO (member to confirm) | Merged by Timo Clement (no separate reviewer recorded); TODO: note how the workflow was checked |
| 2026-10-16 | Menu endpoint `GET /restaurants/{restaurant_id}/menu` and `MenuService` (#34) | PR #59 (`1bb27f3`) | TODO (member to confirm) | TODO (member to confirm) | Quinn Handy | TODO (member to confirm) | Reviewed and merged by Timo Clement; `tests/test_restaurant_menu.py` |
| 2026-10-16 | Update restaurant endpoint `PATCH /restaurants/{restaurant_id}` (#36) | PR #60 (`56bb90d`) | TODO (member to confirm) | TODO (member to confirm) | Timo Clement | TODO (member to confirm) | Reviewed and merged by Quinn Handy; `tests/test_update_restaurant.py` |
| 2026-10-16 | Add menu item endpoint `POST /restaurants/{restaurant_id}/menu` (#37) | PR #61 (`a2014fc`) | TODO (member to confirm) | TODO (member to confirm) | Timo Clement | TODO (member to confirm) | Reviewed and merged by Quinn Handy; `tests/test_add_menu_item.py` |
| 2026-10-16 | Owner web page with create/update form (`app/static/owner.html`, `app/static/owner.js`) (#40) | PR #62 (`2f14dd9`, `cf39d96`, `7559cb3`) | TODO (member to confirm) | TODO (member to confirm) | Samuel Mwanduka | TODO (member to confirm) | Reviewed and merged by Quinn Handy; `tests/test_frontend.py`, `tests/test_restaurant_management_flow.py` |
| 2026-10-16 | Decision receipts (`docs/decision-receipt.md`) (#45) | PR #63 (`40a8c01`, `d7edcd6`) | TODO (member to confirm) | TODO (member to confirm) | Samuel Mwanduka | TODO (member to confirm) | Reviewed and merged by Quinn Handy; TODO: note any check against the code |
| 2026-09-24 to 2026-10-16 | README (`README.md`) | Quinn Handy: PR #3, #12, #47, #53; Asher Nathan: PR #10, #16, #20; Timo Clement: PR #17; Samuel Mwanduka: PR #52, #55, #62; M1 update: PR for #46 | TODO (member to confirm) | TODO (member to confirm) | Quinn Handy, Asher Nathan, Timo Clement, Samuel Mwanduka (each for their own PRs) | TODO (member to confirm) | Reviewed in each PR; TODO: confirm the setup and test commands were run |
| TODO | Level 1 DFD (diagram made outside the repo) | Not in repo. TODO: add link or file location | TODO (member to confirm) | TODO (member to confirm) | TODO | TODO (member to confirm) | TODO |
| TODO (merge date) | M1 README update, this provenance file, and sprint notes (`scrum/sprint-notes-m1.md`) (#46) | PR for #46 | TODO (member to confirm) | TODO (member to confirm) | Quinn Handy | TODO (member to confirm) | `python -m pytest` passes (documentation only); TODO: reviewer |

## How to add an entry

1. Add a row to the table in the **same PR** as the work it describes.
2. Fill in every column. Use the PR number (and commit hashes if useful) so the work can be traced.
3. Pick the label that honestly describes how the work was produced. If AI or an outside source was used, name the tool or cite the URL, and say what part it helped with.
4. Describe how you verified the work: which tests cover it, who reviewed it, and any manual checks.
5. Only list yourself as responsible for work you can explain, test, and defend.
