from datetime import datetime, timezone


def test_due_date_rule_overdue():
    from src.linter.rules.due_date_rule import evaluate_due_date

    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    due = "2026-01-08T00:00:00Z"
    result = evaluate_due_date(due, now=now)

    assert result["overdue"] is True
    assert result["days_past_due"] == 2


def test_due_date_rule_not_overdue():
    from src.linter.rules.due_date_rule import evaluate_due_date

    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    due = "2026-01-12T00:00:00Z"
    result = evaluate_due_date(due, now=now)

    assert result["overdue"] is False
    assert result["days_past_due"] == 0


def test_due_date_rule_trello_format():
    from src.linter.rules.due_date_rule import evaluate_due_date

    now = datetime(2026, 1, 28, tzinfo=timezone.utc)
    due = "2026-01-27T16:48:00.000Z"
    result = evaluate_due_date(due, now=now)

    assert result["overdue"] is True
    assert result["days_past_due"] == 0


def test_due_date_rule_missing_due():
    from src.linter.rules.due_date_rule import evaluate_due_date

    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    result = evaluate_due_date(None, now=now)

    assert result["overdue"] is False
    assert result["days_past_due"] == 0


def test_due_date_rule_invalid_due():
    from src.linter.rules.due_date_rule import evaluate_due_date

    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    result = evaluate_due_date("not-a-date", now=now)

    assert result["overdue"] is False
    assert result["days_past_due"] == 0
