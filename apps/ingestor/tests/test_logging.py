import io
import json
import logging

from ingestor.logging_config import JsonLogFormatter, configure_logging, log_structured


def test_json_log_formatter_serializes_structured_fields():
    stream = io.StringIO()
    logger = logging.getLogger("test.ingestor.json")
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonLogFormatter())
    logger.addHandler(handler)

    log_structured(
        logger,
        logging.WARNING,
        "message_discarded",
        topic="dsm/prod/app/interacao/tela",
        error="Invalid schema_version",
        raw_payload='{"schema_version": "2.0"}',
    )

    line = stream.getvalue().strip()
    parsed = json.loads(line)
    assert parsed["level"] == "WARNING"
    assert parsed["logger"] == "test.ingestor.json"
    assert parsed["event"] == "message_discarded"
    assert parsed["topic"] == "dsm/prod/app/interacao/tela"
    assert parsed["error"] == "Invalid schema_version"
    assert parsed["raw_payload"] == '{"schema_version": "2.0"}'
    assert "timestamp" in parsed


def test_configure_logging_is_idempotent():
    logger_name = "test.ingestor.idempotent"
    logger = logging.getLogger(logger_name)
    logger.handlers.clear()

    first = configure_logging(level="DEBUG", logger_name=logger_name)
    second = configure_logging(level="INFO", logger_name=logger_name)

    assert first is second
    assert len(second.handlers) == 1
    assert isinstance(second.handlers[0].formatter, JsonLogFormatter)
    assert second.level == logging.INFO
