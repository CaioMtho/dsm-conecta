import math
import random
import uuid
from datetime import UTC, datetime

from schemas import EventCategory, EventSource, TelemetryEvent


def _poisson_sample(lam: float) -> int:
    if lam <= 0:
        return 0
    limit = math.exp(-lam)
    k = 0
    prob = 1.0
    while True:
        k += 1
        prob *= random.random()
        if prob <= limit:
            return k - 1


def create_visitor_event(
    people_per_minute: float,
    interval_seconds: float,
    session_id: str,
) -> TelemetryEvent:
    expected_visitors = (people_per_minute / 60.0) * interval_seconds
    visitor_count = _poisson_sample(expected_visitors)

    return TelemetryEvent(
        timestamp=datetime.now(UTC),
        event_id=str(uuid.uuid4()),
        session_id=session_id,
        source=EventSource.SENSOR_SIMULATOR,
        category=EventCategory.CONTAGEM_ESTANDE,
        payload={
            "visitor_count": visitor_count,
            "interval_seconds": interval_seconds,
            "configured_rate_per_min": people_per_minute,
        },
    )
