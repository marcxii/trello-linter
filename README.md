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

## Tests
`pytest -q`
