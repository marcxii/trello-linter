from src.controllers import export_controller


def test_export_csv_missing_run_id_returns_400(client):
    res = client.get("/export/findings.csv")
    assert res.status_code == 400
    assert b"Missing run_id" in res.data


def test_export_csv_unknown_run_returns_404(client):
    res = client.get("/export/findings.csv?run_id=999999")
    assert res.status_code == 404
    assert b"Not found" in res.data


def test_slugify_board_name_fallback_and_cleanup():
    assert export_controller._slugify_board_name("  ") == "board"
    assert export_controller._slugify_board_name("Board: Name?!") == "Board Name"


def test_apply_rule_settings_overrides_returns_base_when_empty():
    base = {"card_due_date": {"enabled": True}}
    merged = export_controller._apply_rule_settings_overrides(base, {})
    assert merged is base


def test_apply_rule_settings_overrides_updates_threshold_section():
    base = {"progress_monitoring": {"threshold_num_days": 5}}
    overrides = {"progress_monitoring": {"threshold_num_days": 9}}
    merged = export_controller._apply_rule_settings_overrides(base, overrides)
    assert merged["progress_monitoring"]["threshold_num_days"] == 9
