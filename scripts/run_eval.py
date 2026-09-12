import json
import time
from pathlib import Path

from triage_iq.pipeline import PipelineError, run_ticket
from triage_iq.schemas import IncomingTicket

EVAL_SET_PATH = Path("data/eval_set.json")
RESULTS_PATH = Path("data/eval_results.json")


def load_eval_set() -> list[dict]:
    return json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))


def run_eval() -> None:
    eval_rows = load_eval_set()
    results = []

    print(f"Running {len(eval_rows)} ticket(s) from {EVAL_SET_PATH} ...\n")

    for row in eval_rows:
        ticket = IncomingTicket(
            ticket_id=row["ticket_id"],
            subject=row["subject"],
            body=row["body"],
        )

        try:
            start = time.perf_counter()
            response = run_ticket(ticket)
            latency_ms = (time.perf_counter() - start) * 1000

            actual_category = response.classification.category.value
            actual_urgency = response.classification.urgency.value
            actual_action = response.routing_decision.action.value

            category_match = actual_category == row["expected_category"]
            urgency_match = actual_urgency == row["expected_urgency"]
            action_match = actual_action == row["expected_action"]

            result = {
                "ticket_id": ticket.ticket_id,
                "expected_category": row["expected_category"],
                "actual_category": actual_category,
                "category_match": category_match,
                "expected_urgency": row["expected_urgency"],
                "actual_urgency": actual_urgency,
                "urgency_match": urgency_match,
                "expected_action": row["expected_action"],
                "actual_action": actual_action,
                "action_match": action_match,
                "summary": response.classification.summary,
                "confidence": response.classification.confidence,
                "latency_ms": round(latency_ms, 1),
                "error": None,
            }

        except PipelineError as exc:
            result = {
                "ticket_id": ticket.ticket_id,
                "expected_category": row["expected_category"],
                "actual_category": None,
                "category_match": False,
                "expected_urgency": row["expected_urgency"],
                "actual_urgency": None,
                "urgency_match": False,
                "expected_action": row["expected_action"],
                "actual_action": None,
                "action_match": False,
                "summary": None,
                "confidence": None,
                "latency_ms": None,
                "error": f"failed at stage '{exc.stage}': {exc.original}",
            }
            print(
                f"  [ERROR] {ticket.ticket_id} failed at stage '{exc.stage}': {exc.original}"
            )

        results.append(result)

    _print_report(results)
    _save_results(results)


def _print_report(results: list[dict]) -> None:
    total = len(results)
    failed = sum(1 for r in results if r["error"] is not None)
    scored = [r for r in results if r["error"] is None]

    category_acc = sum(r["category_match"] for r in scored) / total * 100
    urgency_acc = sum(r["urgency_match"] for r in scored) / total * 100
    action_acc = sum(r["action_match"] for r in scored) / total * 100

    print("\n" + "=" * 72)
    print(f"{'ticket_id':<10}{'category':<10}{'urgency':<10}{'action':<10}")
    print("=" * 72)
    for r in results:
        if r["error"] is not None:
            print(f"{r['ticket_id']:<10}{'ERROR':<10}{'ERROR':<10}{'ERROR':<10}")
            continue
        cat_mark = "OK" if r["category_match"] else "MISS"
        urg_mark = "OK" if r["urgency_match"] else "MISS"
        act_mark = "OK" if r["action_match"] else "MISS"
        print(f"{r['ticket_id']:<10}{cat_mark:<10}{urg_mark:<10}{act_mark:<10}")

    print("=" * 72)
    print(f"Category accuracy: {category_acc:.1f}%")
    print(f"Urgency accuracy:  {urgency_acc:.1f}%")
    print(f"Action accuracy:   {action_acc:.1f}%")
    print(f"Failed to run:     {failed}/{total}")
    print("=" * 72)

    mismatches = [
        r
        for r in scored
        if not (r["category_match"] and r["urgency_match"] and r["action_match"])
    ]
    if mismatches:
        print("\nMismatch details:\n")
        for r in mismatches:
            print(f"--- {r['ticket_id']} ---")
            print(
                f"  category: expected={r['expected_category']!r} actual={r['actual_category']!r}"
            )
            print(
                f"  urgency:  expected={r['expected_urgency']!r} actual={r['actual_urgency']!r}"
            )
            print(
                f"  action:   expected={r['expected_action']!r} actual={r['actual_action']!r}"
            )
            print(f"  summary:    {r['summary']}")
            print(f"  confidence: {r['confidence']:.2f}")
            print()


def _save_results(results: list[dict]) -> None:
    RESULTS_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Full results saved to {RESULTS_PATH}")


if __name__ == "__main__":
    run_eval()
