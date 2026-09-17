from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from api.dashboard import router as dashboard_router
from triage_iq.db import crud
from triage_iq.db.connection import get_session
from triage_iq.pipeline import PipelineError, run_ticket
from triage_iq.schemas import (
    EscalationRecord,
    FinalResponse,
    IncomingTicket,
    RagAnswer,
    RoutingAction,
    RoutingDecision,
    TicketCategory,
    TicketClassification,
    TicketRecord,
    TicketUrgency,
)

app = FastAPI(title="TriageIQ", version="0.1.0")
app.include_router(dashboard_router)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/dashboard", StaticFiles(directory=STATIC_DIR, html=True), name="dashboard")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(PipelineError)
def handle_pipeline_error(request, exc: PipelineError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "ticket_id": exc.ticket_id,
            "stage": exc.stage,
            "detail": str(exc.original),
        },
    )


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard/")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/tickets", response_model=FinalResponse)
@limiter.limit("5/minute")
def submit_ticket(request: Request, ticket: IncomingTicket) -> FinalResponse:
    return run_ticket(ticket)


@app.get("/tickets/{ticket_id}", response_model=TicketRecord)
def get_ticket(ticket_id: str) -> TicketRecord:
    with get_session() as session:
        row = crud.get_ticket(session, ticket_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket '{ticket_id}' not found",
            )

        classification = None
        if row.classification is not None:
            c = row.classification
            classification = TicketClassification(
                category=TicketCategory(c.category),
                urgency=TicketUrgency(c.urgency),
                summary=(c.summary),
                confidence=(c.confidence),
            )

        routing_decision = None
        if row.routing_decision is not None:
            r = row.routing_decision
            routing_decision = RoutingDecision(
                action=RoutingAction(r.action), reasoning=r.reasoning
            )

        rag_answer = None
        if row.rag_answer is not None:
            a = row.rag_answer
            rag_answer = RagAnswer(
                answer=a.answer,
                source_documents=a.source_documents,
                grounded=a.grounded,
            )

        escalation = None
        if row.escalation is not None:
            e = row.escalation
            escalation = EscalationRecord(
                escalation_id=e.escalation_id,
                assigned_team=e.assigned_team,
                priority=e.priority,
                trello_card_url=e.trello_card_url,
            )

        return TicketRecord(
            ticket_id=row.ticket_id,
            subject=row.subject,
            body=row.body,
            classification=classification,
            routing_decision=routing_decision,
            rag_answer=rag_answer,
            escalation=escalation,
        )


@app.get("/tickets/{ticket_id}/logs")
def get_ticket_logs(ticket_id: str) -> list[dict]:
    with get_session() as session:
        ticket = crud.get_ticket(session, ticket_id)
        if ticket is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket '{ticket_id}' not found",
            )

        logs = crud.get_logs_for_ticket(session, ticket_id)
        return [
            {
                "stage": log.stage,
                "message": log.message,
                "latency_ms": log.latency_ms,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ]
