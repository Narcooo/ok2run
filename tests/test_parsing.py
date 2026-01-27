import pytest

from agent_approval_gate.decision import ParseError, parse_menu_reply


def test_parse_simple_codes():
    assert parse_menu_reply("2").code == "2"
    assert parse_menu_reply("3").code == "3"


def test_parse_note_and_override():
    decision = parse_menu_reply("4 add logs")
    assert decision.code == "4"
    assert decision.note == "add logs"

    decision = parse_menu_reply("5 npm test")
    assert decision.code == "5"
    assert decision.override == "npm test"


def test_parse_invalid_missing_payload():
    with pytest.raises(ParseError):
        parse_menu_reply("4")
    with pytest.raises(ParseError):
        parse_menu_reply("5")
