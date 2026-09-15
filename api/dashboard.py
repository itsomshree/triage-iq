from fastapi import APIRouter, Query

from triage_iq.db import crud
from triage_iq.db.connection import get_session

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_URGENCY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


@router.get("/summary")
def get_summary() -> dict:
    with get_session() as session:
        action_counts = crud.get_routing_action_counts(session)
        return {
            "total_tickets": crud.get_total_ticket_count(session),
            "auto_answer_count": action_counts.get("auto_answer", 0),
            "escalate_count": action_counts.get("escalate", 0),
            "flag_for_review_count": action_counts.get("flag_for_review", 0),
            "avg_confidence": crud.get_avg_confidence(session),
            "avg_latency_ms": crud.get_avg_pipeline_latency_ms(session),
        }


@router.get("/category-breakdown")
def get_category_breakdown() -> list[dict]:
    with get_session() as session:
        counts = crud.get_category_counts(session)

    return [
        {"category": category, "count": count}
        for category, count in sorted(counts.items(), key=lambda kv: -kv[1])
    ]


@router.get("/urgency-breakdown")
def get_urgency_breakdown() -> list[dict]:
    with get_session() as session:
        counts = crud.get_urgency_counts(session)

    return [
        {"urgency": urgency, "count": count}
        for urgency, count in sorted(
            counts.items(), key=lambda kv: _URGENCY_ORDER.get(kv[0], 99)
        )
    ]


@router.get("/recent-tickets")
def get_recent_tickets(limit: int = Query(default=25, ge=1, le=100)) -> list[dict]:
    with get_session() as session:
        tickets = crud.get_recent_tickets(session, limit=limit)

        results = []
        for ticket in tickets:
            classification = ticket.classification
            routing_decision = ticket.routing_decision
            results.append(
                {
                    "ticket_id": ticket.ticket_id,
                    "subject": ticket.subject,
                    "category": classification.category if classification else None,
                    "urgency": classification.urgency if classification else None,
                    "confidence": (
                        classification.confidence if classification else None
                    ),
                    "action": routing_decision.action if routing_decision else None,
                    "created_at": (
                        ticket.created_at.isoformat() if ticket.created_at else None
                    ),
                }
            )
        return results
