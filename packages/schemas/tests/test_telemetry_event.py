from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from schemas.events import (
    TelemetryEvent,
    EventSource,
    EventCategory,
    SUPPORTED_SCHEMA_VERSION,
)


def test_valid_telemetry_event_from_dict():
    raw_data = {
        "schema_version": "1.0",
        "timestamp": "2026-08-26T19:30:00Z",
        "event_id": "evt_12345",
        "session_id": "sess_abcde123",
        "source": "app_mobile",
        "category": "interacao_tela",
        "payload": {
            "screen_name": "matriz_curricular",
            "duration_ms": 1200,
        },
    }

    event = TelemetryEvent.model_validate(raw_data)

    assert event.schema_version == SUPPORTED_SCHEMA_VERSION
    assert event.event_id == "evt_12345"
    assert event.session_id == "sess_abcde123"
    assert event.source == EventSource.APP_MOBILE
    assert event.category == EventCategory.INTERACAO_TELA
    assert event.payload["screen_name"] == "matriz_curricular"
    assert event.payload["duration_ms"] == 1200
    assert event.timestamp == datetime(2026, 8, 26, 19, 30, 0, tzinfo=timezone.utc)


def test_telemetry_event_from_json_string():
    json_str = """
    {
        "schema_version": "1.0",
        "timestamp": "2026-08-26T19:30:00Z",
        "event_id": "evt_999",
        "session_id": "sess_xyz",
        "source": "sensor_simulator",
        "category": "contagem_estande",
        "payload": {"visitor_count": 5}
    }
    """
    event = TelemetryEvent.model_validate_json(json_str)

    assert event.event_id == "evt_999"
    assert event.source == EventSource.SENSOR_SIMULATOR
    assert event.category == EventCategory.CONTAGEM_ESTANDE
    assert event.payload == {"visitor_count": 5}


def test_telemetry_event_serialization_json():
    event = TelemetryEvent(
        schema_version="1.0",
        timestamp=datetime(2026, 8, 26, 19, 30, 0, tzinfo=timezone.utc),
        event_id="evt_001",
        session_id="sess_001",
        source=EventSource.APP_WEB,
        category=EventCategory.QUESTIONARIO_VOCACIONAL,
        payload={"recommended_area": "Desenvolvimento Multiplataforma"},
    )
    json_output = event.model_dump_json()
    assert "evt_001" in json_output
    assert "sess_001" in json_output
    assert "questionario_vocacional" in json_output


def test_telemetry_event_rejects_unsupported_schema_version():
    raw_data = {
        "schema_version": "2.0",
        "timestamp": "2026-08-26T19:30:00Z",
        "event_id": "evt_12345",
        "session_id": "sess_abcde123",
        "source": "app_mobile",
        "category": "interacao_tela",
        "payload": {},
    }
    with pytest.raises(ValidationError) as exc_info:
        TelemetryEvent.model_validate(raw_data)
    assert "schema_version" in str(exc_info.value)


def test_telemetry_event_rejects_missing_required_fields():
    # Sem event_id e session_id
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


def test_telemetry_event_rejects_invalid_source_or_category():
    raw_data = {
        "schema_version": "1.0",
        "timestamp": "2026-08-26T19:30:00Z",
        "event_id": "evt_123",
        "session_id": "sess_123",
        "source": "invalid_source",
        "category": "invalid_category",
        "payload": {},
    }
    with pytest.raises(ValidationError):
        TelemetryEvent.model_validate(raw_data)
