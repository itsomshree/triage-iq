import time
from collections.abc import Iterator
from contextlib import contextmanager

from triage_iq.chains.classifier_chain import classify_ticket
from triage_iq.chains.escalation_chain import escalate
from triage_iq.chains.rag_chain import answer_ticket
from triage_iq.chains.routing_chain import decide_routing
from triage_iq.db import crud
from triage_iq.db.connection import get_session
from triage_iq.logging_utils import log_stage, timer
from triage_iq.schemas import (
    FinalResponse,
    IncomingTicket,
    RoutingAction,
    RoutingDecision,
)


class PipelineError(Exception):
    def __init__(self, ticket_id: str, stage: str, original: Exception) -> None:
        self.ticket_id = ticket_id
        self.stage = stage
        self.original = original
        super().__init__(
            f"Pipeline failed for ticket {ticket_id} at stage '{stage}': {original}"
        )


@contextmanager
def _stage(name: str) -> Iterator[None]:
    try:
        yield
    except Exception as exc:
        exc.stage = name  # type: ignore[attr-defined]
        raise


def run_ticket(ticket: IncomingTicket) -> FinalResponse:
    total_start = time.perf_counter()

    with get_session() as session:
        try:
            with _stage("ticket_creation"):
                crud.create_ticket(session, ticket)

            # classification
            with _stage("classification"), timer() as t:
                classification = classify_ticket(ticket)
            log_stage(
                session,
                ticket.ticket_id,
                "classification",
                f"category={classification.category.value} "
                f"urgency={classification.urgency.value} "
                f"confidence={classification.confidence:.2f}",
                t.ms,
            )
            crud.save_classification(session, ticket.ticket_id, classification)

            # routing
            with _stage("routing"), timer() as t:
                routing_decision = decide_routing(classification)
            log_stage(
                session,
                ticket.ticket_id,
                "routing",
                f"action={routing_decision.action.value}",
                t.ms,
            )

            rag_answer = None
            escalation = None

            if routing_decision.action == RoutingAction.AUTO_ANSWER:
                with _stage("rag_answer"), timer() as t:
                    rag_answer = answer_ticket(ticket)
                log_stage(
                    session,
                    ticket.ticket_id,
                    "rag_answer",
                    f"grounded={rag_answer.grounded}",
                    t.ms,
                )
                crud.save_rag_answer(session, ticket.ticket_id, rag_answer)

                if not rag_answer.grounded:
                    routing_decision = RoutingDecision(
                        action=RoutingAction.ESCALATE,
                        reasoning=(
                            "RAG attempt did not produce a grounded answer; "
                            "escalating."
                        ),
                    )
                    log_stage(
                        session,
                        ticket.ticket_id,
                        "routing_override",
                        "auto_answer failed groundedness check, escalating instead",
                    )

            crud.save_routing_decision(session, ticket.ticket_id, routing_decision)

            if routing_decision.action == RoutingAction.ESCALATE:
                with _stage("escalation"), timer() as t:
                    escalation = escalate(ticket, classification, routing_decision)
                log_stage(
                    session,
                    ticket.ticket_id,
                    "escalation",
                    f"assigned_team={escalation.assigned_team} "
                    f"priority={escalation.priority}",
                    t.ms,
                )

            total_latency_ms = (time.perf_counter() - total_start) * 1000

            return FinalResponse(
                ticket_id=ticket.ticket_id,
                classification=classification,
                routing_decision=routing_decision,
                rag_answer=rag_answer,
                escalation=escalation,
                latency_ms=total_latency_ms,
            )

        except Exception as exc:
            stage = getattr(exc, "stage", "unknown")
            session.rollback()
            log_stage(session, ticket.ticket_id, "pipeline_error", f"FAILED: {exc}")
            session.commit()
            raise PipelineError(ticket.ticket_id, stage, exc) from exc
