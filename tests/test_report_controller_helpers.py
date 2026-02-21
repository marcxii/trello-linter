from src.controllers import report_controller


def test_format_display_date_handles_valid_invalid_and_empty():
    assert report_controller._format_display_date("2026-02-12T12:30:00.000Z") == "Feb 12, 2026"
    assert report_controller._format_display_date("not-a-date") == "not-a-date"
    assert report_controller._format_display_date(None) == ""


def test_apply_rule_settings_overrides_updates_flags_and_thresholds():
    base = {
        "card_due_date": {"enabled": True},
        "progress_threshold": {"max_wip_per_member": 3},
    }
    overrides = {
        "rules": {"card_due_date": False},
        "progress_threshold": {"max_wip_per_member": 9},
    }
    merged = report_controller._apply_rule_settings_overrides(base, overrides)
    assert merged["card_due_date"]["enabled"] is False
    assert merged["progress_threshold"]["max_wip_per_member"] == 9


def test_apply_rule_settings_overrides_returns_base_when_empty():
    base = {"card_due_date": {"enabled": True}}
    merged = report_controller._apply_rule_settings_overrides(base, {})
    assert merged is base
