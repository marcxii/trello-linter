from src.linter.rules.flow_rules import get_last_activity_date, get_moved_to_in_progress_date


def test_get_last_activity_date_prefers_date_last_activity():
    card = {"dateLastActivity": "2026-02-01T12:00:00.000Z", "actions": []}
    dt = get_last_activity_date(card)
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 2


def test_get_last_activity_date_falls_back_to_actions():
    card = {
        "actions": [{"date": "2026-01-31T10:00:00.000Z"}],
    }
    dt = get_last_activity_date(card)
    assert dt is not None
    assert dt.day == 31


def test_get_last_activity_date_invalid_inputs_return_none():
    card = {"dateLastActivity": "not-a-date", "actions": [{"date": "also-bad"}]}
    assert get_last_activity_date(card) is None


def test_get_moved_to_in_progress_date_detects_update_action():
    card = {
        "actions": [
            {
                "type": "updateCard",
                "date": "2026-01-20T09:30:00.000Z",
                "data": {"listAfter": {"name": "In Progress"}, "listBefore": {"name": "Backlog"}},
            }
        ]
    }
    dt = get_moved_to_in_progress_date(card)
    assert dt is not None
    assert dt.day == 20


def test_get_moved_to_in_progress_date_returns_none_without_matching_action():
    card = {"actions": [{"type": "commentCard", "date": "2026-01-20T09:30:00.000Z"}]}
    assert get_moved_to_in_progress_date(card) is None
