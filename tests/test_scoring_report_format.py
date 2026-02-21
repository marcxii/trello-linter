from src.linter.scoring_engine import calculate_overall_score, format_score_report


def test_format_score_report_contains_summary_sections():
    results = [
        {"rule_id": "card_ownership", "fail_count": 1, "eligible_count": 10},
        {"rule_id": "card_due_date", "fail_count": 0, "eligible_count": 10},
    ]
    scoring = calculate_overall_score(results)
    report = format_score_report(scoring)
    assert "TRELLO BOARD QUALITY SCORE" in report
    assert "Individual Rule Scores" in report
    assert "card_ownership" in report
    assert "card_due_date" in report
