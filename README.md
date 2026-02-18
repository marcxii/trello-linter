# Trello Board Linter

## A tool to analyze Trello board exports and generate quality reports

## Run locally

### 1) Create a virtual environment (recommended)
`python -m venv .venv`
`source .venv/bin/activate`

### 2) Install dependencies
`pip install -r requirements.txt`

### 3) Start the server
Option A (recommended):
`python -m flask --app src.main run --debug`

Option B:
`python src/main.py`

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
- Results page includes:
  - Quick Stats and Overall Quality Score.
  - Past-due cards populated from stored data with "View Card" buttons.
  - Filter by member dropdown (multi-select) with Apply to refresh results.
- "View Card" opens a card detail partial with member/list/due info and a Back to Report button.
- Back to Report restores the results partial for the same `run_id`.
- Printable Report opens a modal overlay with report sections; Settings opens a report settings overlay.
- Report settings allow toggling rules and adjusting thresholds. Disabled rules are hidden and not scored.
- Settings persist for the session and apply to new analyses. Saving settings refreshes the report view.
- Full-page report is available at `/report/<run_id>`.
- Help button opens a slide-up FAQ panel (single item open at a time).

## Tests
`pytest -q`

## Example boards
Sample Trello JSON fixtures for manual validation are in `examples/boards/`:
- `example_violates_all_rules.json`
- `example_score_below_50.json`
- `example_score_above_90.json`
- `example_progress_threshold_5_members_3_violations.json`
