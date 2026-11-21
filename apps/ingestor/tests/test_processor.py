import io
import json
import logging
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from ingestor.logging_config import JsonLogFormatter
from ingestor.processor import MessageProcessor, ProcessingStatus
from schemas import EventCategory, EventSource, TelemetryEvent

VALID_EVENT_ID = "550e8400-e29b-41d4-a716-446655440000"
VALID_SESSION_ID = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"


def _make_json_logger(name: str) -> tuple[logging.Logger, io.StringIO]:
    stream = io.StringIO()
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonLogFormatter())
    logger.addHandler(handler)
    return logger, stream


def _valid_payload_dict(**overrides) -> dict:
    data = {
        "schema_version": "1.0",
        "timestamp": "2026-11-21T18:00:00Z",
        "event_id": VALID_EVENT_ID,
        "session_id": VALID_SESSION_ID,
        "source": "app_mobile",
        "category": "interacao_tela",
        "payload": {"screen_name": "cursos", "duration_seconds": 3.5},
    }
    data.update(overrides)
    return data


async def test_processor_persists_valid_telemetry_event():
    repo = AsyncMock()
    logger, stream = _make_json_logger("test.processor.valid")
    processor = MessageProcessor(repository=repo, logger=logger)

    raw_bytes = json.dumps(_valid_payload_dict()).encode("utf-8")
    status = await processor.process_message("dsm/prod/app/interacao/tela", raw_bytes)

    assert status == ProcessingStatus.PERSISTED
    repo.insert_event.assert_awaited_once()
    persisted: TelemetryEvent = repo.insert_event.await_args.args[0]
    assert persisted.event_id == VALID_EVENT_ID
    assert persisted.session_id == VALID_SESSION_ID
    assert persisted.source == EventSource.APP_MOBILE
    assert persisted.category == EventCategory.INTERACAO_TELA
    assert persisted.timestamp == datetime(2026, 11, 21, 18, 0, 0, tzinfo=UTC)

    log_entry = json.loads(stream.getvalue().strip())
    assert log_entry["level"] == "INFO"
    assert log_entry["event"] == "event_persisted"
    assert log_entry["topic"] == "dsm/prod/app/interacao/tela"
    assert log_entry["event_id"] == VALID_EVENT_ID


@pytest.mark.parametrize("status_value", ["online", "offline"])
async def test_processor_records_valid_device_status_without_db_insert(status_value: str):
    repo = AsyncMock()
    logger, stream = _make_json_logger(f"test.processor.status.{status_value}")
    processor = MessageProcessor(repository=repo, logger=logger)

    raw = json.dumps({"status": status_value}).encode("utf-8")
    result = await processor.process_message("dsm/prod/totem/sensor/status", raw)

    assert result == ProcessingStatus.STATUS_RECORDED
    repo.insert_event.assert_not_awaited()

    log_entry = json.loads(stream.getvalue().strip())
    assert log_entry["level"] == "INFO"
    assert log_entry["event"] == "device_status_received"
    assert log_entry["topic"] == "dsm/prod/totem/sensor/status"
    assert log_entry["status"] == status_value


async def test_processor_discards_malformed_status_payload_with_json_log():
    repo = AsyncMock()
    logger, stream = _make_json_logger("test.processor.bad_status")
    processor = MessageProcessor(repository=repo, logger=logger)

    raw_text = '{"state": "unknown"}'
    result = await processor.process_message(
        "dsm/prod/totem/sensor/status", raw_text.encode("utf-8")
    )

    assert result == ProcessingStatus.DISCARDED
    repo.insert_event.assert_not_awaited()

    log_entry = json.loads(stream.getvalue().strip())
    assert log_entry["level"] == "WARNING"
    assert log_entry["event"] == "message_discarded"
    assert log_entry["topic"] == "dsm/prod/totem/sensor/status"
    assert log_entry["raw_payload"] == raw_text
    assert log_entry["error"]


async def test_processor_discards_invalid_utf8_payload():
    repo = AsyncMock()
    logger, stream = _make_json_logger("test.processor.utf8")
    processor = MessageProcessor(repository=repo, logger=logger)

    result = await processor.process_message("dsm/prod/app/interacao/tela", b"\xff\xfe\x00")

    assert result == ProcessingStatus.DISCARDED
    repo.insert_event.assert_not_awaited()

    log_entry = json.loads(stream.getvalue().strip())
    assert log_entry["level"] == "WARNING"
    assert log_entry["event"] == "message_discarded"
    assert log_entry["topic"] == "dsm/prod/app/interacao/tela"
    assert "UTF-8" in log_entry["error"]
    assert log_entry["raw_payload"] == repr(b"\xff\xfe\x00")


@pytest.mark.parametrize(
    ("label", "raw_payload"),
    [
        ("malformed_json", "{not-valid-json"),
        ("json_array", '["not", "an", "object"]'),
        (
            "missing_schema_version",
            json.dumps(
                {k: v for k, v in _valid_payload_dict().items() if k != "schema_version"}
            ),
        ),
        (
            "incompatible_schema_version",
            json.dumps(_valid_payload_dict(schema_version="2.0")),
        ),
        (
            "non_uuid_event_id",
            json.dumps(_valid_payload_dict(event_id="evt_12345")),
        ),
        (
            "non_uuid_session_id",
            json.dumps(_valid_payload_dict(session_id="sim-session-abc")),
        ),
        (
            "naive_timestamp",
            json.dumps(_valid_payload_dict(timestamp="2026-11-21T18:00:00")),
        ),
        (
            "invalid_source",
            json.dumps(_valid_payload_dict(source="unknown_device")),
        ),
        (
            "invalid_category",
            json.dumps(_valid_payload_dict(category="invalid_cat")),
        ),
        (
            "extra_field",
            json.dumps(_valid_payload_dict(unexpected="value")),
        ),
        (
            "non_dict_payload",
            json.dumps(_valid_payload_dict(payload="invalid")),
        ),
    ],
)
async def test_processor_discards_invalid_messages_with_structured_json_log(
    label: str, raw_payload: str
):
    repo = AsyncMock()
    logger, stream = _make_json_logger(f"test.processor.invalid.{label}")
    processor = MessageProcessor(repository=repo, logger=logger)
    topic = "dsm/prod/app/interacao/tela"

    result = await processor.process_message(topic, raw_payload.encode("utf-8"))

    assert result == ProcessingStatus.DISCARDED
    repo.insert_event.assert_not_awaited()

    log_entry = json.loads(stream.getvalue().strip())
    assert log_entry["level"] == "WARNING"
    assert log_entry["event"] == "message_discarded"
    assert log_entry["topic"] == topic
    assert log_entry["raw_payload"] == raw_payload
    assert log_entry["error"]


async def test_processor_continues_after_malformed_message():
    repo = AsyncMock()
    logger, stream = _make_json_logger("test.processor.resilience")
    processor = MessageProcessor(repository=repo, logger=logger)

    first = await processor.process_message("dsm/prod/app/interacao/tela", b"{broken")
    second = await processor.process_message(
        "dsm/prod/totem/sensor/contagem",
        json.dumps(
            _valid_payload_dict(
                source="sensor_simulator",
                category="contagem_estande",
                payload={"visitor_count": 4},
            )
        ).encode("utf-8"),
    )

    assert first == ProcessingStatus.DISCARDED
    assert second == ProcessingStatus.PERSISTED
    repo.insert_event.assert_awaited_once()
    lines = [json.loads(line) for line in stream.getvalue().strip().splitlines()]
    assert [entry["event"] for entry in lines] == ["message_discarded", "event_persisted"]


async def test_processor_handles_persistence_error_without_crashing():
    repo = AsyncMock()
    repo.insert_event.side_effect = RuntimeError("connection dropped")
    logger, stream = _make_json_logger("test.processor.db_error")
    processor = MessageProcessor(repository=repo, logger=logger)

    result = await processor.process_message(
        "dsm/prod/app/interacao/tela",
        json.dumps(_valid_payload_dict()).encode("utf-8"),
    )

    assert result == ProcessingStatus.PERSISTENCE_ERROR
    log_entry = json.loads(stream.getvalue().strip())
    assert log_entry["level"] == "ERROR"
    assert log_entry["event"] == "persistence_failed"
    assert log_entry["topic"] == "dsm/prod/app/interacao/tela"
    assert log_entry["event_id"] == VALID_EVENT_ID
    assert "connection dropped" in log_entry["error"]
