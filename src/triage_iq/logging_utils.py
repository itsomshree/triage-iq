import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy.orm import Session

from triage_iq.db import crud

logger = logging.getLogger("triage_iq")
logging.basicConfig(level=logging.INFO)


@dataclass
class _Elapsed:
    ms: float = 0.0


@contextmanager
def timer():
    result = _Elapsed()
    start = time.perf_counter()
    try:
        yield result
    finally:
        result.ms = (time.perf_counter() - start) * 1000


def log_stage(
    session: Session,
    ticket_id: str,
    stage: str,
    message: str,
    latency_ms: float | None = None,
) -> None:
    crud.add_log(
        session,
        ticket_id=ticket_id,
        stage=stage,
        message=message,
        latency_ms=latency_ms,
    )
    suffix = f" ({latency_ms:.1f}ms)" if latency_ms is not None else ""
    logger.info("[%s] %s: %s%s", ticket_id, stage, message, suffix)
