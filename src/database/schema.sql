-- =====================================================
-- Trello Board Linter - Complete Database Schema
-- =====================================================
-- SQLite schema for storing analysis runs, findings, and reports
--
-- Design Philosophy:
-- - Separate tables for queryable data (findings, cards)
-- - JSON blobs for complex nested data (report summaries)
-- - Session-based cleanup for temporary storage
-- - Foreign keys for referential integrity

-- =====================================================
-- Core Tables
-- =====================================================

-- Runs: Each analysis of a Trello board
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    created_at TEXT NOT NULL,              -- ISO 8601 datetime
    board_ref TEXT NOT NULL,               -- Board name or filename
    
    -- Board metadata
    board_id TEXT,                         -- Trello board ID
    board_name TEXT,
    board_desc TEXT,
    
    -- Counts
    cards_count INTEGER DEFAULT 0,
    lists_count INTEGER DEFAULT 0,
    members_count INTEGER DEFAULT 0,
    
    -- Scores
    overall_score REAL,                    -- 0-100
    category_scores TEXT,                  -- JSON: {"Story Quality": 85, ...}
    
    -- Finding counts (denormalized for quick access)
    total_findings INTEGER DEFAULT 0,
    critical_findings INTEGER DEFAULT 0,
    major_findings INTEGER DEFAULT 0,
    minor_findings INTEGER DEFAULT 0,
    
    -- Metadata
    overdue_count INTEGER DEFAULT 0,
    report_json TEXT,                      -- Full report blob for exports
    
    -- Indexes
    CONSTRAINT session_created_idx UNIQUE (session_id, created_at)
);

CREATE INDEX IF NOT EXISTS idx_runs_session 
    ON runs(session_id);

CREATE INDEX IF NOT EXISTS idx_runs_created 
    ON runs(created_at);


-- =====================================================
-- Cards: Individual Trello cards from the board
-- =====================================================
CREATE TABLE IF NOT EXISTS cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    
    -- Card identification
    card_id TEXT,                          -- Trello card ID
    card_name TEXT NOT NULL,
    card_desc TEXT,
    
    -- Card metadata
    list_id TEXT,                          -- Which list it's in
    list_name TEXT,                        -- Denormalized for convenience
    due TEXT,                              -- ISO 8601 datetime
    is_closed BOOLEAN DEFAULT 0,
    
    -- Members (JSON array of member IDs)
    members TEXT,                          -- JSON: ["member1", "member2"]
    
    -- Labels (JSON array)
    labels TEXT,                           -- JSON: [{"name": "High Priority", "color": "red"}]
    
    -- Checklist IDs (JSON array)
    checklists TEXT,                       -- JSON: ["checklist1", "checklist2"]
    
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cards_run 
    ON cards(run_id);

CREATE INDEX IF NOT EXISTS idx_cards_due 
    ON cards(due);

CREATE INDEX IF NOT EXISTS idx_cards_list 
    ON cards(list_id);


-- =====================================================
-- Findings: Individual rule violations/issues
-- =====================================================
CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    card_id TEXT,                          -- Trello card ID (NULL for board-level findings)
    card_name TEXT,
    
    -- Rule information
    rule_name TEXT NOT NULL,               -- "User Story Format", "Done Evidence", etc.
    category TEXT NOT NULL,                -- "Story Quality", "Ownership", etc.
    severity TEXT NOT NULL,                -- "critical", "major", "minor"
    
    -- Finding details
    description TEXT NOT NULL,             -- What's wrong
    suggestion TEXT,                       -- How to fix it
    
    -- Metadata
    created_at TEXT NOT NULL,              -- ISO 8601 datetime
    
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE,
    
    -- Ensure severity is valid
    CHECK (severity IN ('critical', 'major', 'minor'))
);

CREATE INDEX IF NOT EXISTS idx_findings_run 
    ON findings(run_id);

CREATE INDEX IF NOT EXISTS idx_findings_severity 
    ON findings(severity);

CREATE INDEX IF NOT EXISTS idx_findings_category 
    ON findings(category);

CREATE INDEX IF NOT EXISTS idx_findings_card 
    ON findings(card_id);


-- =====================================================
-- Lists: Board lists/columns
-- =====================================================
CREATE TABLE IF NOT EXISTS lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    
    list_id TEXT NOT NULL,                 -- Trello list ID
    list_name TEXT NOT NULL,
    is_closed BOOLEAN DEFAULT 0,
    position INTEGER,                      -- Order on the board
    
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_lists_run 
    ON lists(run_id);


-- =====================================================
-- Members: Board members/collaborators
-- =====================================================
CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    
    member_id TEXT NOT NULL,               -- Trello member ID
    full_name TEXT,
    username TEXT,
    
    -- Workload stats (calculated during analysis)
    active_cards_count INTEGER DEFAULT 0,
    
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_members_run 
    ON members(run_id);


-- =====================================================
-- Checklists: Acceptance criteria and task lists
-- =====================================================
CREATE TABLE IF NOT EXISTS checklists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    card_id TEXT,                          -- Trello card ID
    
    checklist_id TEXT NOT NULL,            -- Trello checklist ID
    checklist_name TEXT,
    
    -- Checklist stats
    total_items INTEGER DEFAULT 0,
    completed_items INTEGER DEFAULT 0,
    completion_rate REAL DEFAULT 0.0,      -- 0.0 to 1.0
    
    -- Full items as JSON
    items_json TEXT,                       -- JSON array of check items
    
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_checklists_run 
    ON checklists(run_id);

CREATE INDEX IF NOT EXISTS idx_checklists_card 
    ON checklists(card_id);


-- =====================================================
-- Category Scores: Detailed scoring breakdown
-- =====================================================
CREATE TABLE IF NOT EXISTS category_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    
    category_name TEXT NOT NULL,           -- "Story Quality", "Ownership", etc.
    score REAL NOT NULL,                   -- 0-100
    weight REAL NOT NULL,                  -- 0.0-1.0 (e.g., 0.30 for 30%)
    
    -- Finding breakdown for this category
    critical_count INTEGER DEFAULT 0,
    major_count INTEGER DEFAULT 0,
    minor_count INTEGER DEFAULT 0,
    
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE,
    UNIQUE (run_id, category_name)
);

CREATE INDEX IF NOT EXISTS idx_category_scores_run 
    ON category_scores(run_id);


-- =====================================================
-- Useful Views
-- =====================================================

-- View: Recent runs with summary stats
CREATE VIEW IF NOT EXISTS v_recent_runs AS
SELECT 
    r.id,
    r.session_id,
    r.created_at,
    r.board_name,
    r.overall_score,
    r.total_findings,
    r.critical_findings,
    r.major_findings,
    r.minor_findings,
    r.cards_count,
    r.members_count,
    COUNT(DISTINCT c.id) as stored_cards_count
FROM runs r
LEFT JOIN cards c ON c.run_id = r.id
GROUP BY r.id
ORDER BY r.created_at DESC;


-- View: Findings with card details
CREATE VIEW IF NOT EXISTS v_findings_detail AS
SELECT 
    f.id as finding_id,
    f.run_id,
    r.board_name,
    r.created_at as run_created_at,
    f.card_id,
    f.card_name,
    f.rule_name,
    f.category,
    f.severity,
    f.description,
    f.suggestion,
    c.list_name,
    c.due as card_due
FROM findings f
JOIN runs r ON f.run_id = r.id
LEFT JOIN cards c ON f.card_id = c.card_id AND c.run_id = f.run_id;


-- View: Category performance across runs
CREATE VIEW IF NOT EXISTS v_category_performance AS
SELECT 
    cs.category_name,
    AVG(cs.score) as avg_score,
    MIN(cs.score) as min_score,
    MAX(cs.score) as max_score,
    COUNT(cs.id) as run_count
FROM category_scores cs
GROUP BY cs.category_name;