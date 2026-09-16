import json
import urllib.parse
import urllib.request
from typing import Any
from urllib.error import HTTPError

from triage_iq.config import TRELLO_API_KEY, TRELLO_API_TOKEN, TRELLO_BOARD_NAME

_API_BASE = "https://api.trello.com/1"

_TEAM_LIST_NAMES = {
    "billing": "Billing",
    "logistics": "Logistics",
    "engineering": "Engineering",
    "account_security": "Account Security",
    "support": "Support",
}

_PRIORITY_LABEL_COLORS = {
    "PQ": "red",
    "P1": "orange",
    "P2": "yellow",
    "P3": "green",
}

_board_id: str | None = None
_list_ids: dict[str, str] = {}
_label_ids: dict[str, str] = {}


def _request(method: str, path: str, params: dict[str, Any] | None = None) -> Any:
    query: dict[str, Any] = {"key": TRELLO_API_KEY, "token": TRELLO_API_TOKEN}
    query.update({k: v for k, v in (params or {}).items() if v is not None})
    url = f"{_API_BASE}{path}?{urllib.parse.urlencode(query)}"

    req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read()
            return json.loads(body) if body else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Trello API {method} {path} failed ({exc.code}): {detail}"
        ) from exc


def _request_dict(
    method: str, path: str, params: dict[str, Any] | None = None
) -> dict[str, Any]:
    result = _request(method, path, params)
    assert isinstance(result, dict)
    return result


def _request_list(
    method: str, path: str, params: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    result = _request(method, path, params)
    assert isinstance(result, list)
    return result


def _find_board(name: str) -> dict[str, Any] | None:
    boards = _request_list("GET", "/members/me/boards", {"fields": "name"})
    return next((b for b in boards if b["name"] == name), None)


def _find_or_create_list(board_id: str, name: str) -> str:
    lists = _request_list("GET", f"/boards/{board_id}/lists", {"fields": "name"})
    existing = next((lst for lst in lists if lst["name"] == name), None)
    if existing:
        return existing["id"]
    created = _request_dict("POST", "/lists", {"name": name, "idBoard": board_id})
    return created["id"]


def _find_or_create_label(board_id: str, name: str, color: str) -> str:
    labels = _request_list(
        "GET", f"/boards/{board_id}/labels", {"fields": "name,color"}
    )
    existing = next((lbl for lbl in labels if lbl["name"] == name), None)
    if existing:
        return existing["id"]
    created = _request_dict(
        "POST", "/labels", {"name": name, "color": color, "idBoard": board_id}
    )
    return created["id"]


def _ensure_board_setup() -> None:
    global _board_id
    if _board_id is not None:
        return

    board = _find_board(TRELLO_BOARD_NAME) or _request_dict(
        "POST", "/boards", {"name": TRELLO_BOARD_NAME, "defaultLists": "false"}
    )
    board_id: str = board["id"]
    _board_id = board_id

    for team, list_name in _TEAM_LIST_NAMES.items():
        _list_ids[team] = _find_or_create_list(board_id, list_name)

    for priority, color in _PRIORITY_LABEL_COLORS.items():
        _label_ids[priority] = _find_or_create_label(board_id, priority, color)


def get_list_id(team: str) -> str:
    _ensure_board_setup()
    return _list_ids.get(team, next(iter(_list_ids.values())))


def get_label_id(priority: str) -> str | None:
    _ensure_board_setup()
    return _label_ids.get(priority)


def create_card(
    *, list_id: str, label_id: str | None, name: str, description: str
) -> dict[str, Any]:
    params: dict[str, Any] = {"idList": list_id, "name": name, "desc": description}
    if label_id:
        params["idLabels"] = label_id
    return _request_dict("POST", "/cards", params)
