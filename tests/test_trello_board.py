import json
from unittest.mock import MagicMock, patch

import pytest

from triage_iq.integrations import trello_board


@pytest.fixture(autouse=True)
def reset_trello_cache():
    trello_board._board_id = None
    trello_board._list_ids.clear()
    trello_board._label_ids.clear()
    yield
    trello_board._board_id = None
    trello_board._list_ids.clear()
    trello_board._label_ids.clear()


def _mock_response(payload):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = False
    return mock_resp


def test_find_board_returns_match_by_name():
    boards = [
        {"id": "b1", "name": "Other"},
        {"id": "b2", "name": "TriageIQ Escalations"},
    ]
    with patch("urllib.request.urlopen", return_value=_mock_response(boards)):
        found = trello_board._find_board("TriageIQ Escalations")
    assert found == {"id": "b2", "name": "TriageIQ Escalations"}


def test_find_board_returns_none_when_missing():
    with patch("urllib.request.urlopen", return_value=_mock_response([])):
        found = trello_board._find_board("TriageIQ Escalations")
    assert found is None


def test_find_or_create_list_reuses_existing():
    existing_lists = [{"id": "list-1", "name": "Billing"}]
    with patch(
        "urllib.request.urlopen", return_value=_mock_response(existing_lists)
    ) as mock_open:
        list_id = trello_board._find_or_create_list("board-1", "Billing")
    assert list_id == "list-1"
    assert mock_open.call_count == 1


def test_find_or_create_list_creates_when_missing():
    responses = [_mock_response([]), _mock_response({"id": "list-new"})]
    with patch("urllib.request.urlopen", side_effect=responses):
        list_id = trello_board._find_or_create_list("board-1", "Engineering")
    assert list_id == "list-new"


def test_find_or_create_label_creates_when_missing():
    responses = [_mock_response([]), _mock_response({"id": "label-new"})]
    with patch("urllib.request.urlopen", side_effect=responses):
        label_id = trello_board._find_or_create_label("board-1", "PQ", "red")
    assert label_id == "label-new"


def test_ensure_board_setup_reuses_everything_when_already_provisioned():
    responses = (
        [_mock_response([{"id": "board-1", "name": trello_board.TRELLO_BOARD_NAME}])]
        + [
            _mock_response([{"id": f"list-{name}", "name": name}])
            for name in trello_board._TEAM_LIST_NAMES.values()
        ]
        + [
            _mock_response([{"id": f"label-{p}", "name": p}])
            for p in trello_board._PRIORITY_LABEL_COLORS
        ]
    )
    with patch("urllib.request.urlopen", side_effect=responses):
        trello_board._ensure_board_setup()

    assert trello_board._board_id == "board-1"
    assert set(trello_board._list_ids) == set(trello_board._TEAM_LIST_NAMES)
    assert set(trello_board._label_ids) == set(trello_board._PRIORITY_LABEL_COLORS)


def test_get_list_id_only_provisions_once():
    responses = (
        [_mock_response([{"id": "board-1", "name": trello_board.TRELLO_BOARD_NAME}])]
        + [
            _mock_response([{"id": f"list-{name}", "name": name}])
            for name in trello_board._TEAM_LIST_NAMES.values()
        ]
        + [
            _mock_response([{"id": f"label-{p}", "name": p}])
            for p in trello_board._PRIORITY_LABEL_COLORS
        ]
    )
    with patch("urllib.request.urlopen", side_effect=responses) as mock_open:
        trello_board.get_list_id("billing")
        call_count_after_first = mock_open.call_count
        trello_board.get_list_id("engineering")

    assert mock_open.call_count == call_count_after_first


def test_create_card_includes_label_when_given():
    with patch(
        "urllib.request.urlopen",
        return_value=_mock_response(
            {"id": "card-1", "shortUrl": "https://trello.com/c/abc"}
        ),
    ):
        card = trello_board.create_card(
            list_id="list-1",
            label_id="label-1",
            name="Charged twice",
            description="details",
        )
    assert card["shortUrl"] == "https://trello.com/c/abc"
