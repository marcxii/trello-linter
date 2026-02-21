import json

import pytest

from src.parser.trello_parser import (
    TrelloParseError,
    get_cards_in_list,
    get_list_by_name,
    load_trello_file,
    parse_full_board,
)


def test_parse_full_board_includes_card_fields():
    payload = {
        "id": "b1",
        "name": "Parser Board",
        "desc": "Board description",
        "lists": [{"id": "l1", "name": "In Progress", "closed": False}],
        "cards": [
            {
                "id": "c1",
                "name": "Card 1",
                "idList": "l1",
                "desc": "Some description",
                "dateLastActivity": "2026-02-01T00:00:00.000Z",
                "idMembers": ["m1"],
                "labels": [{"name": "Label"}],
                "idChecklists": ["cl1"],
                "closed": False,
                "due": "2026-02-10T12:00:00.000Z",
                "shortUrl": "https://trello.com/c/abc123",
                "actions": [{"type": "updateCard"}],
            }
        ],
        "members": [{"id": "m1", "fullName": "Alex", "username": "alex"}],
        "checklists": [{"id": "cl1", "name": "Checklist", "checkItems": [{"name": "Item"}]}],
    }

    parsed = parse_full_board(payload)
    assert parsed["board"]["name"] == "Parser Board"
    assert parsed["cards"][0]["short_url"] == "https://trello.com/c/abc123"
    assert parsed["cards"][0]["dateLastActivity"] == "2026-02-01T00:00:00.000Z"
    assert parsed["cards"][0]["due"] == "2026-02-10T12:00:00.000Z"


def test_parse_full_board_handles_missing_optional_sections():
    payload = {"name": "Minimal Board"}
    parsed = parse_full_board(payload)
    assert parsed["lists"] == []
    assert parsed["cards"] == []
    assert parsed["members"] == []
    assert parsed["checklists"] == []


def test_get_list_by_name_is_case_insensitive():
    payload = {"lists": [{"id": "l1", "name": "Done"}, {"id": "l2", "name": "Backlog"}]}
    found = get_list_by_name(payload, "done")
    assert found is not None
    assert found["id"] == "l1"


def test_get_cards_in_list_filters_by_idlist():
    payload = {
        "cards": [
            {"id": "c1", "name": "One", "idList": "l1"},
            {"id": "c2", "name": "Two", "idList": "l2"},
            {"id": "c3", "name": "Three", "idList": "l1"},
        ]
    }
    cards = get_cards_in_list(payload, "l1")
    assert [card["id"] for card in cards] == ["c1", "c3"]


def test_load_trello_file_rejects_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{ not-json", encoding="utf-8")
    with pytest.raises(TrelloParseError):
        load_trello_file(str(path))


def test_load_trello_file_rejects_missing_board_name(tmp_path):
    path = tmp_path / "missing_name.json"
    path.write_text(json.dumps({"cards": []}), encoding="utf-8")
    with pytest.raises(TrelloParseError):
        load_trello_file(str(path))
