"""Database management functions for Trello Board Linter.

This module provides simple functions for database operations.
No classes - just functions that work with SQLite connections.

Usage:
    from src.database.db_functions import init_database, save_run, get_run_summary
    
    # In Flask route/controller
    db = get_db()  # Uses Flask config for DB path
    save_findings(db, run_id, findings_list)
    
    # Save analysis
    run_id = save_run(conn, session_id, board_data, scores)
    
    # Retrieve
    summary = get_run_summary(conn, run_id)
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# -------------------------
# Run Management
# -------------------------

def save_run(
    conn: sqlite3.Connection,
    session_id: str,
    board_data: Dict[str, Any],
    scores: Dict[str, Any],
    report_json: Optional[Dict[str, Any]] = None
) -> int:
    """Save an analysis run to the database.
    
    Args:
        conn: SQLite connection
        session_id: User session ID
        board_data: Parsed board data (from parse_full_board)
        scores: Calculated scores (from scorer)
        report_json: Optional full report JSON for exports
        
    Returns:
        run_id: ID of the created run
    """
    created_at = datetime.now(timezone.utc).isoformat()
    board_info = board_data.get('board', {})
    
    cursor = conn.execute("""
        INSERT INTO runs (
            session_id, created_at, board_ref, board_id, board_name, board_desc,
            cards_count, lists_count, members_count,
            overall_score, category_scores,
            total_findings, critical_findings, major_findings, minor_findings,
            report_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id,
        created_at,
        board_info.get('name', 'Unknown Board'),
        board_info.get('id'),
        board_info.get('name'),
        board_info.get('desc', ''),
        len(board_data.get('cards', [])),
        len(board_data.get('lists', [])),
        len(board_data.get('members', [])),
        scores.get('overall_score', 0),
        json.dumps(scores.get('category_scores', {})),
        scores.get('total_findings', 0),
        scores.get('critical_findings', 0),
        scores.get('major_findings', 0),
        scores.get('minor_findings', 0),
        json.dumps(report_json) if report_json else None
    ))
    
    run_id = cursor.lastrowid
    conn.commit()
    return run_id


def update_run_scores(
    conn: sqlite3.Connection,
    run_id: int,
    scores: Dict[str, Any]
) -> None:
    """Update scores for an existing run.
    
    Args:
        conn: SQLite connection
        run_id: Run ID to update
        scores: Updated scores dictionary
    """
    conn.execute("""
        UPDATE runs SET
            overall_score = ?,
            category_scores = ?,
            total_findings = ?,
            critical_findings = ?,
            major_findings = ?,
            minor_findings = ?
        WHERE id = ?
    """, (
        scores.get('overall_score', 0),
        json.dumps(scores.get('category_scores', {})),
        scores.get('total_findings', 0),
        scores.get('critical_findings', 0),
        scores.get('major_findings', 0),
        scores.get('minor_findings', 0),
        run_id
    ))
    conn.commit()


def get_run_summary(conn: sqlite3.Connection, run_id: int) -> Optional[Dict[str, Any]]:
    """Get summary information for a run.
    
    Args:
        conn: SQLite connection
        run_id: Run ID to retrieve
        
    Returns:
        Dictionary with run summary, or None if not found
    """
    cursor = conn.execute("""
        SELECT * FROM runs WHERE id = ?
    """, (run_id,))
    
    row = cursor.fetchone()
    if not row:
        return None
    
    return {
        'id': row['id'],
        'session_id': row['session_id'],
        'created_at': row['created_at'],
        'board_name': row['board_name'],
        'overall_score': row['overall_score'],
        'category_scores': json.loads(row['category_scores']) if row['category_scores'] else {},
        'total_findings': row['total_findings'],
        'critical_findings': row['critical_findings'],
        'major_findings': row['major_findings'],
        'minor_findings': row['minor_findings'],
        'cards_count': row['cards_count'],
        'members_count': row['members_count'],
    }


# -------------------------
# Findings Management
# -------------------------

def save_findings(
    conn: sqlite3.Connection,
    run_id: int,
    findings: List[Dict[str, Any]]
) -> None:
    """Save findings to the database.
    
    Args:
        conn: SQLite connection
        run_id: Run ID these findings belong to
        findings: List of finding dictionaries from rule engine
    """
    created_at = datetime.now(timezone.utc).isoformat()
    
    rows = []
    for finding in findings:
        rows.append((
            run_id,
            finding.get('card_id'),
            finding.get('card_name'),
            finding.get('rule_name'),
            finding.get('category'),
            finding.get('severity'),
            finding.get('description'),
            finding.get('suggestion'),
            created_at
        ))
    
    conn.executemany("""
        INSERT INTO findings (
            run_id, card_id, card_name, rule_name, category, severity,
            description, suggestion, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    
    conn.commit()


def get_findings_for_run(
    conn: sqlite3.Connection,
    run_id: int,
    severity: Optional[str] = None,
    category: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get findings for a specific run with optional filters.
    
    Args:
        conn: SQLite connection
        run_id: Run ID to get findings for
        severity: Optional filter by severity ("critical", "major", "minor")
        category: Optional filter by category
        
    Returns:
        List of finding dictionaries
    """
    query = "SELECT * FROM findings WHERE run_id = ?"
    params = [run_id]
    
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    
    if category:
        query += " AND category = ?"
        params.append(category)
    
    query += " ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'major' THEN 2 ELSE 3 END"
    
    cursor = conn.execute(query, params)
    
    findings = []
    for row in cursor.fetchall():
        findings.append({
            'id': row['id'],
            'card_id': row['card_id'],
            'card_name': row['card_name'],
            'rule_name': row['rule_name'],
            'category': row['category'],
            'severity': row['severity'],
            'description': row['description'],
            'suggestion': row['suggestion'],
        })
    
    return findings


# -------------------------
# Cards Management
# -------------------------

def save_members(
    conn: sqlite3.Connection,
    run_id: int,
    members: List[Dict[str, Any]],
) -> None:
    """Save board members to the database.

    Args:
        conn: SQLite connection
        run_id: Run ID these members belong to
        members: List of member dicts from parser
    """
    rows = []
    for member in members:
        if not member.get("id"):
            continue
        rows.append((
            run_id,
            member.get('id'),
            member.get('fullName'),
            member.get('username'),
        ))

    if not rows:
        return

    conn.executemany("""
        INSERT INTO members (
            run_id, member_id, full_name, username
        ) VALUES (?, ?, ?, ?)
    """, rows)

    conn.commit()


def get_members_for_run(conn: sqlite3.Connection, run_id: int) -> Dict[str, str]:
    """Return mapping of member_id -> display name for a run."""
    cursor = conn.execute("""
        SELECT member_id, full_name, username
        FROM members
        WHERE run_id = ?
    """, (run_id,))

    mapping = {}
    for row in cursor.fetchall():
        name = row["full_name"] or row["username"] or row["member_id"]
        mapping[row["member_id"]] = name

    return mapping


def save_cards(
    conn: sqlite3.Connection,
    run_id: int,
    cards: List[Dict[str, Any]],
    list_map: Dict[str, str] = None
) -> None:
    """Save cards to the database.
    
    Args:
        conn: SQLite connection
        run_id: Run ID these cards belong to
        cards: List of card dictionaries from parser
        list_map: Optional mapping of list_id to list_name
    """
    list_map = list_map or {}
    
    rows = []
    for card in cards:
        rows.append((
            run_id,
            card.get('id'),
            card.get('name'),
            card.get('desc', ''),
            card.get('list_id'),
            list_map.get(card.get('list_id'), ''),
            card.get('due'),
            card.get('closed', False),
            json.dumps(card.get('members', [])),
            json.dumps(card.get('labels', [])),
            json.dumps(card.get('checklists', []))
        ))
    
    conn.executemany("""
        INSERT INTO cards (
            run_id, card_id, card_name, card_desc, list_id, list_name,
            due, is_closed, members, labels, checklists
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    
    conn.commit()


def get_cards_for_run(conn: sqlite3.Connection, run_id: int) -> List[Dict[str, Any]]:
    """Get all cards for a specific run.
    
    Args:
        conn: SQLite connection
        run_id: Run ID
        
    Returns:
        List of card dictionaries
    """
    cursor = conn.execute("""
        SELECT * FROM cards WHERE run_id = ?
    """, (run_id,))
    
    cards = []
    for row in cursor.fetchall():
        cards.append({
            'id': row['id'],
            'card_id': row['card_id'],
            'card_name': row['card_name'],
            'card_desc': row['card_desc'],
            'list_id': row['list_id'],
            'list_name': row['list_name'],
            'due': row['due'],
            'is_closed': row['is_closed'],
            'members': json.loads(row['members']) if row['members'] else [],
            'labels': json.loads(row['labels']) if row['labels'] else [],
            'checklists': json.loads(row['checklists']) if row['checklists'] else [],
        })
    
    return cards


def get_card_for_run(conn: sqlite3.Connection, run_id: int, card_id: str) -> Optional[Dict[str, Any]]:
    """Get a single card by Trello card_id for a run."""
    cursor = conn.execute("""
        SELECT * FROM cards WHERE run_id = ? AND card_id = ? LIMIT 1
    """, (run_id, card_id))

    row = cursor.fetchone()
    if not row:
        return None

    return {
        'id': row['id'],
        'card_id': row['card_id'],
        'card_name': row['card_name'],
        'card_desc': row['card_desc'],
        'list_id': row['list_id'],
        'list_name': row['list_name'],
        'due': row['due'],
        'is_closed': row['is_closed'],
        'members': json.loads(row['members']) if row['members'] else [],
        'labels': json.loads(row['labels']) if row['labels'] else [],
        'checklists': json.loads(row['checklists']) if row['checklists'] else [],
    }


def get_findings_for_card(
    conn: sqlite3.Connection,
    run_id: int,
    card_id: str,
) -> List[Dict[str, Any]]:
    """Get findings for a specific card in a run."""
    cursor = conn.execute("""
        SELECT * FROM findings
        WHERE run_id = ? AND card_id = ?
        ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'major' THEN 2 ELSE 3 END
    """, (run_id, card_id))

    findings = []
    for row in cursor.fetchall():
        findings.append({
            'id': row['id'],
            'card_id': row['card_id'],
            'card_name': row['card_name'],
            'rule_name': row['rule_name'],
            'category': row['category'],
            'severity': row['severity'],
            'description': row['description'],
            'suggestion': row['suggestion'],
        })

    return findings


# -------------------------
# Cleanup Functions
# -------------------------

def cleanup_old_runs(conn: sqlite3.Connection, ttl_seconds: int) -> int:
    """Delete runs older than TTL.
    
    Args:
        conn: SQLite connection
        ttl_seconds: Time to live in seconds
        
    Returns:
        Number of runs deleted
    """
    cutoff_time = datetime.now(timezone.utc).timestamp() - ttl_seconds
    cutoff_iso = datetime.fromtimestamp(cutoff_time, tz=timezone.utc).isoformat()
    
    cursor = conn.execute("""
        DELETE FROM runs WHERE created_at < ?
    """, (cutoff_iso,))
    
    deleted = cursor.rowcount
    conn.commit()
    return deleted


def delete_session_runs(conn: sqlite3.Connection, session_id: str) -> int:
    """Delete all runs for a specific session.
    
    Args:
        conn: SQLite connection
        session_id: Session ID to delete
        
    Returns:
        Number of runs deleted
    """
    cursor = conn.execute("""
        DELETE FROM runs WHERE session_id = ?
    """, (session_id,))
    
    deleted = cursor.rowcount
    conn.commit()
    return deleted


# -------------------------
# Query Helpers
# -------------------------

def get_recent_runs(
    conn: sqlite3.Connection,
    session_id: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Get recent runs with summary stats.
    
    Args:
        conn: SQLite connection
        session_id: Optional filter by session ID
        limit: Maximum number of runs to return
        
    Returns:
        List of run summaries
    """
    if session_id:
        cursor = conn.execute("""
            SELECT * FROM v_recent_runs 
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (session_id, limit))
    else:
        cursor = conn.execute("""
            SELECT * FROM v_recent_runs 
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
    
    runs = []
    for row in cursor.fetchall():
        runs.append(dict(row))
    
    return runs


def get_findings_by_category(
    conn: sqlite3.Connection,
    run_id: int
) -> Dict[str, List[Dict[str, Any]]]:
    """Get findings grouped by category.
    
    Args:
        conn: SQLite connection
        run_id: Run ID
        
    Returns:
        Dictionary mapping category names to lists of findings
    """
    cursor = conn.execute("""
        SELECT * FROM findings 
        WHERE run_id = ?
        ORDER BY category, severity
    """, (run_id,))
    
    by_category = {}
    for row in cursor.fetchall():
        category = row['category']
        if category not in by_category:
            by_category[category] = []
        
        by_category[category].append({
            'card_name': row['card_name'],
            'rule_name': row['rule_name'],
            'severity': row['severity'],
            'description': row['description'],
            'suggestion': row['suggestion'],
        })
    
    return by_category
