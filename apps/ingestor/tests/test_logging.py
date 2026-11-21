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


def test_json_log_formatter_preserves_reserved_keys_and_formats_exception():
    stream = io.StringIO()
    logger = logging.getLogger("test.ingestor.reserved")
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonLogFormatter())
    logger.addHandler(handler)

    try:
        raise ValueError("boom")
    except ValueError:
        logger.exception(
            "db_failed",
            extra={
                "structured": {
                    "event": "db_failed",
                    "level": "FORGED",
                    "logger": "forged.logger",
                    "timestamp": "forged-ts",
                    "message": "forged-msg",
                }
            },
        )

    parsed = json.loads(stream.getvalue().strip())
    assert parsed["level"] == "ERROR"
    assert parsed["logger"] == "test.ingestor.reserved"
    assert parsed["timestamp"] != "forged-ts"
    assert parsed["message"] == "db_failed"
    assert parsed["event"] == "db_failed"
    assert "ValueError: boom" in parsed["exception"]

    stream.truncate(0)
    stream.seek(0)
    try:
        raise RuntimeError("structured_boom")
    except RuntimeError:
        log_structured(
            logger,
            logging.ERROR,
            "db_failed",
            exc_info=True,
            timestamp="forged-ts",
        )

    parsed_helper = json.loads(stream.getvalue().strip())
    assert parsed_helper["timestamp"] != "forged-ts"
    assert "RuntimeError: structured_boom" in parsed_helper["exception"]


def test_configure_logging_is_idempotent_and_safe_against_non_level_names():
    logger_name = "test.ingestor.idempotent"
    logger = logging.getLogger(logger_name)
    logger.handlers.clear()

    first = configure_logging(level="DEBUG", logger_name=logger_name)
    second = configure_logging(level="Logger", logger_name=logger_name)

    assert first is second
    assert len(second.handlers) == 1
    assert isinstance(second.handlers[0].formatter, JsonLogFormatter)
    assert second.level == logging.INFO
