from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError
from schemas.events import (
    SUPPORTED_SCHEMA_VERSION,
    EventCategory,
    EventSource,
    TelemetryEvent,
)

VALID_EVENT_ID = "550e8400-e29b-41d4-a716-446655440000"
VALID_SESSION_ID = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"


def test_valid_telemetry_event_from_dict():
    raw_data = {
        "schema_version": "1.0",
        "timestamp": "2026-08-26T19:30:00Z",
        "event_id": VALID_EVENT_ID,
        "session_id": VALID_SESSION_ID,
        "source": "app_mobile",
        "category": "interacao_tela",
        "payload": {
            "screen_name": "matriz_curricular",
            "duration_ms": 1200,
        },
    }

    event = TelemetryEvent.model_validate(raw_data)

    assert event.schema_version == SUPPORTED_SCHEMA_VERSION
    assert event.event_id == VALID_EVENT_ID
    assert event.session_id == VALID_SESSION_ID
    assert event.source == EventSource.APP_MOBILE
    assert event.category == EventCategory.INTERACAO_TELA
    assert event.payload["screen_name"] == "matriz_curricular"
    assert event.payload["duration_ms"] == 1200
    assert event.timestamp == datetime(2026, 8, 26, 19, 30, 0, tzinfo=UTC)


def test_telemetry_event_from_json_string():
    json_str = f"""
    {{
        "schema_version": "1.0",
        "timestamp": "2026-08-26T19:30:00Z",
        "event_id": "{VALID_EVENT_ID}",
        "session_id": "{VALID_SESSION_ID}",
        "source": "sensor_simulator",
        "category": "contagem_estande",
        "payload": {{"visitor_count": 5}}
    }}
    """
    event = TelemetryEvent.model_validate_json(json_str)

    assert event.event_id == VALID_EVENT_ID
    assert event.source == EventSource.SENSOR_SIMULATOR
    assert event.category == EventCategory.CONTAGEM_ESTANDE
    assert event.payload == {"visitor_count": 5}


def test_telemetry_event_normalizes_uuid_objects_and_uppercase_strings():
    event = TelemetryEvent(
        schema_version="1.0",
        timestamp=datetime(2026, 8, 26, 19, 30, 0, tzinfo=UTC),
        event_id=UUID(VALID_EVENT_ID),
        session_id=f"  {VALID_SESSION_ID.upper()}  ",
        source=EventSource.APP_WEB,
        category=EventCategory.QUESTIONARIO_VOCACIONAL,
        payload={"recommended_area": "Desenvolvimento Multiplataforma"},
    )

    assert event.event_id == VALID_EVENT_ID
    assert event.session_id == VALID_SESSION_ID


def test_telemetry_event_serialization_json():
    event = TelemetryEvent(
        schema_version="1.0",
        timestamp=datetime(2026, 8, 26, 19, 30, 0, tzinfo=UTC),
        event_id=VALID_EVENT_ID,
        session_id=VALID_SESSION_ID,
        source=EventSource.APP_WEB,
        category=EventCategory.QUESTIONARIO_VOCACIONAL,
        payload={"recommended_area": "Desenvolvimento Multiplataforma"},
    )
    json_output = event.model_dump_json()
    assert VALID_EVENT_ID in json_output
    assert VALID_SESSION_ID in json_output
    assert "questionario_vocacional" in json_output


def test_telemetry_event_rejects_unsupported_schema_version():
    raw_data = {
        "schema_version": "2.0",
        "timestamp": "2026-08-26T19:30:00Z",
        "event_id": VALID_EVENT_ID,
        "session_id": VALID_SESSION_ID,
        "source": "app_mobile",
        "category": "interacao_tela",
        "payload": {},
    }
    with pytest.raises(ValidationError) as exc_info:
        TelemetryEvent.model_validate(raw_data)
    assert "schema_version" in str(exc_info.value)


def test_telemetry_event_rejects_missing_required_fields():
    raw_data = {
        "schema_version": "1.0",
        "timestamp": "2026-08-26T19:30:00Z",
        "source": "app_mobile",
        "category": "interacao_tela",
        "payload": {},
    }
    with pytest.raises(ValidationError) as exc_info:
        TelemetryEvent.model_validate(raw_data)
    errors = exc_info.value.errors()
    field_names = [e["loc"][0] for e in errors]
    assert "event_id" in field_names
    assert "session_id" in field_names


def test_telemetry_event_rejects_empty_ids():
    raw_data = {
        "schema_version": "1.0",
        "timestamp": "2026-08-26T19:30:00Z",
        "event_id": "",
        "session_id": "   ",
        "source": "app_mobile",
        "category": "interacao_tela",
        "payload": {},
    }
    with pytest.raises(ValidationError):
        TelemetryEvent.model_validate(raw_data)


@pytest.mark.parametrize(
    ("event_id", "session_id"),
    [
        ("evt_12345", VALID_SESSION_ID),
        (VALID_EVENT_ID, "sim-session-123"),
        ("not-a-uuid", "also-not-a-uuid"),
    ],
)
def test_telemetry_event_rejects_non_uuid_ids(event_id: str, session_id: str):
    raw_data = {
        "schema_version": "1.0",
        "timestamp": "2026-08-26T19:30:00Z",
        "event_id": event_id,
        "session_id": session_id,
        "source": "app_mobile",
        "category": "interacao_tela",
        "payload": {},
    }
    with pytest.raises(ValidationError):
        TelemetryEvent.model_validate(raw_data)


def test_telemetry_event_rejects_naive_timestamp():
    raw_data = {
        "schema_version": "1.0",
        "timestamp": "2026-08-26T19:30:00",
        "event_id": VALID_EVENT_ID,
        "session_id": VALID_SESSION_ID,
        "source": "app_mobile",
        "category": "interacao_tela",
        "payload": {},
    }
    with pytest.raises(ValidationError) as exc_info:
        TelemetryEvent.model_validate(raw_data)
    assert "timestamp" in str(exc_info.value)


def test_telemetry_event_normalizes_aware_timestamp_to_utc():
    brt = timezone(timedelta(hours=-3))
    event = TelemetryEvent(
        schema_version="1.0",
        timestamp=datetime(2026, 8, 26, 16, 30, 0, tzinfo=brt),
        event_id=VALID_EVENT_ID,
        session_id=VALID_SESSION_ID,
        source=EventSource.APP_MOBILE,
        category=EventCategory.INTERACAO_TELA,
        payload={},
    )
    assert event.timestamp == datetime(2026, 8, 26, 19, 30, 0, tzinfo=UTC)
    assert event.timestamp.tzinfo == UTC


def test_telemetry_event_rejects_invalid_source_or_category():
    raw_data = {
        "schema_version": "1.0",
        "timestamp": "2026-08-26T19:30:00Z",
        "event_id": VALID_EVENT_ID,
        "session_id": VALID_SESSION_ID,
        "source": "invalid_source",
        "category": "invalid_category",
        "payload": {},
    }
    with pytest.raises(ValidationError):
        TelemetryEvent.model_validate(raw_data)


def test_telemetry_event_rejects_extra_fields_and_non_dict_payload():
    with pytest.raises(ValidationError):
        TelemetryEvent.model_validate(
            {
                "schema_version": "1.0",
                "timestamp": "2026-08-26T19:30:00Z",
                "event_id": VALID_EVENT_ID,
                "session_id": VALID_SESSION_ID,
                "source": "app_mobile",
                "category": "interacao_tela",
                "payload": {},
                "unexpected": True,
            }
        )

    with pytest.raises(ValidationError):
        TelemetryEvent.model_validate(
            {
                "schema_version": "1.0",
                "timestamp": "2026-08-26T19:30:00Z",
                "event_id": VALID_EVENT_ID,
                "session_id": VALID_SESSION_ID,
                "source": "app_mobile",
                "category": "interacao_tela",
                "payload": ["not", "a", "dict"],
            }
        )
