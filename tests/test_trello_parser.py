def test_parse_board_summary_counts():
    from src.parser.trello_parser import parse_board_summary

    payload = {
        "name": "Demo Board",
        "cards": [{"name": "Card A"}, {"name": "Card B"}],
        "members": [{"id": "m1"}, {"id": "m2"}, {"id": "m3"}],
    }

    summary = parse_board_summary(payload)

    assert summary["board_name"] == "Demo Board"
    assert summary["cards_count"] == 2
    assert summary["members_count"] == 3
