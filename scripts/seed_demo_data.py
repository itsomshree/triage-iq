import argparse
import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SAMPLE_TICKETS_PATH = Path("data/sample_tickets.json")
EVAL_SET_PATH = Path("data/eval_set.json")

DEFAULT_URL = os.getenv("TRIAGE_IQ_API_URL", "http://localhost:8000")


def load_tickets(source: str) -> list[dict]:
    tickets: list[dict] = []

    if source in ("sample", "both"):
        tickets.extend(json.loads(SAMPLE_TICKETS_PATH.read_text(encoding="utf-8")))

    if source in ("eval", "both"):
        eval_rows = json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))
        for row in eval_rows:
            tickets.append(
                {
                    "ticket_id": row["ticket_id"],
                    "subject": row["subject"],
                    "body": row["body"],
                }
            )

    return tickets


def _request(url: str, method: str = "GET", payload: dict | None = None) -> dict | None:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = Request(url, data=data, headers=headers, method=method)

    with urlopen(req, timeout=180) as resp:
        body = resp.read()
        return json.loads(body) if body else None


def already_routed(base_url: str, ticket_id: str) -> bool:
    try:
        record = _request(f"{base_url}/tickets/{ticket_id}")
        return bool(record and record.get("routing_decision"))
    except HTTPError as exc:
        if exc.code == 404:
            return False
        raise


def seed_ticket(base_url: str, ticket: dict) -> None:
    ticket_id = ticket["ticket_id"]

    try:
        response = _request(f"{base_url}/tickets", method="POST", payload=ticket)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"  [ERROR] {ticket_id} -> HTTP {exc.code}: {detail}")
        return
    except URLError as exc:
        print(f"  [ERROR] {ticket_id} -> couldn't reach {base_url}: {exc.reason}")
        return

    assert response is not None
    action = response["routing_decision"]["action"]
    category = response["classification"]["category"]
    print(f"  [OK] {ticket_id} -> {category} / {action}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"Base URL of a running TriageIQ API (default: {DEFAULT_URL}, "
        f"or set TRIAGE_IQ_API_URL)",
    )
    parser.add_argument(
        "--source",
        choices=["sample", "eval", "both"],
        default="both",
        help="Which ticket set(s) to seed from (default: both)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocess tickets even if already routed (re-runs the "
        "LLM/RAG pipeline and adds new log entries)",
    )
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    tickets = load_tickets(args.source)

    print(f"Seeding {len(tickets)} ticket(s) into {base_url} ...\n")

    for ticket in tickets:
        ticket_id = ticket["ticket_id"]

        if not args.force and already_routed(base_url, ticket_id):
            print(f"  [SKIP] {ticket_id} already routed")
            continue

        seed_ticket(base_url, ticket)
        time.sleep(13)

    print("\nDone. Open the dashboard to see the results:")
    print(f"  {base_url}/dashboard/")


if __name__ == "__main__":
    main()
