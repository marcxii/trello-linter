# TrelloScore

## A tool to analyze Trello board exports and generate quality reports

## About this app
**What:** Trello Board Linter is a Flask app that evaluates Trello board JSON exports against configurable quality rules and produces actionable score-based reports.

**Why:** It was developed to help teams quickly identify workflow issues (like overdue work, unclear ownership, and sizing gaps), standardize board hygiene, and improve delivery visibility.

**Developed for:** The Spring 2026 O1 term of Boston University Metropolitan College (BU MET) CS633.

**Developed by:** 
Zach Franchett - Team Lead
Wesley Chen (`wesJchen`) - QA Engineer
Marcus Lofton (`marcxii`) - Developer
Domineike Henderson (`ddhender6`) - Configuration Engineer
Paul Probst (`probst-paul`) UX Designer / Developer
Arsal Siddiqui (`arsalsidd23`) Testing & Design Engineer

## Run locally

### 1) Create a virtual environment (recommended)
`python -m venv .venv`
`source .venv/bin/activate`

### 2) Install dependencies
`pip install -r requirements.txt`

### 3) Start the server
`python -m flask --app src.main run`

### 4) Open the app
Visit `http://127.0.0.1:5000/`

## Configuration (optional)
Environment variables you can set:
- `SECRET_KEY` (defaults to `dev`)
- `SQLITE_DB_PATH` (defaults to `instance/trelloscore.db`)
- `RUN_TTL_SECONDS` (defaults to 21600 seconds / 6 hours)
- `MAX_CONTENT_LENGTH` (defaults to 10 MB)

Default rule definitions live in `config/rules_config.yaml`. User rule settings are stored per-session.

Scoring uses normalized active rule weights (relative shares across enabled/scored rules).  
Optional Effective Denominator settings are available under `scoring.effective_denominator` in `config/rules_config.yaml`.

## UI flows (current)
- Upload JSON on the home page to render the results partial.
- Report settings are opened from the upload screen after a file is selected.
- Report settings allow toggling rules and adjusting thresholds. Disabled rules are hidden and not scored.
- Settings persist for the session and apply to new analyses. Saving settings refreshes the report view.
- Help button opens a slide-up FAQ panel (single item open at a time).
- Results page includes:
  - Quick Stats and Overall Quality Score.
  - Cards that violate active rules, grouped under Findings by Rule, with "View Card" buttons.
  - Filter by member dropdown (multi-select) with Apply to refresh results.
- "View Card" opens a card detail partial with member/list/due info and a Back to Report button.
- Back to Report restores the results partial for the same `run_id`.
- Printable Report opens a modal overlay with report sections.
- Download CSV exports findings for the current `run_id` (and active member filter).

## Tests
`pytest -q`

## Example boards
Sample Trello JSON fixtures for manual validation are in `examples/boards/`:
- `example_violates_all_rules.json`
- `example_score_below_50.json`
- `example_score_above_90.json`
- `example_progress_threshold_5_members_3_violations.json`
