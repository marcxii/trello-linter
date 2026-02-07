# Trello Board Linter - Project Skeleton

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

## UI flows (current)
- Upload JSON on the home page to render the results partial.
- Results page includes:
  - Quick Stats and Overall Quality Score.
  - Past-due cards populated from stored data with "View Card" buttons.
  - Filter by member dropdown (multi-select) with Apply to refresh results.
- "View Card" opens a card detail partial with member/list/due info and a Back to Report button.
- Back to Report restores the results partial for the same `run_id`.
- Printable Report opens a modal overlay with report sections; Settings opens a report settings overlay.
- Full-page report is available at `/report/<run_id>`.
- Help button opens a slide-up FAQ panel (single item open at a time).

## Tests
`pytest -q`
