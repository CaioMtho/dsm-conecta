import json
import logging
from enum import Enum
from typing import Any

import asyncpg
from pydantic import ValidationError
from schemas import TelemetryEvent

from ingestor.logging_config import log_structured
from ingestor.repository import EventRepository

VALID_STATUS_VALUES: frozenset[str] = frozenset({"online", "offline"})
DEFAULT_MAX_PAYLOAD_BYTES = 65536
DEFAULT_MAX_LOG_PAYLOAD_CHARS = 4096
PERSISTENCE_EXCEPTIONS = (
    asyncpg.PostgresError,
    asyncpg.InterfaceError,
    asyncpg.InternalClientError,
    OSError,
    TimeoutError,
    RuntimeError,
    TypeError,
    ValueError,
)


def _reject_json_constant(token: str) -> Any:
    raise ValueError(f"Constante JSON não permitida pela RFC 8259: {token}")


def _contains_nul_character(value: Any) -> bool:
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, str):
            if "\x00" in current:
                return True
        elif isinstance(current, dict):
            stack.extend(current.keys())
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return False


class ProcessingStatus(str, Enum):
    PERSISTED = "persisted"
    DUPLICATE_IGNORED = "duplicate_ignored"
    STATUS_RECORDED = "status_recorded"
    DISCARDED = "discarded"
    PERSISTENCE_ERROR = "persistence_error"


class MessageProcessor:
    def __init__(
        self,
        repository: EventRepository,
        logger: logging.Logger | None = None,
        max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
        max_log_payload_chars: int = DEFAULT_MAX_LOG_PAYLOAD_CHARS,
    ) -> None:
        self._repository = repository
        self._logger = logger or logging.getLogger("ingestor")
        self._max_payload_bytes = max_payload_bytes
        self._max_log_payload_chars = max_log_payload_chars

    async def process_message(
        self,
        topic: str,
        payload: bytes | bytearray | str,
    ) -> ProcessingStatus:
        raw_text = self._decode_payload(topic, payload)
        if raw_text is None:
            return ProcessingStatus.DISCARDED

        if topic.endswith("/status"):
            return self._process_status_message(topic, raw_text)

        event = self._validate_telemetry_event(topic, raw_text)
        if event is None:
            return ProcessingStatus.DISCARDED

        try:
            inserted = await self._repository.insert_event(event)
        except PERSISTENCE_EXCEPTIONS as exc:
            log_structured(
                self._logger,
                logging.ERROR,
                "persistence_failed",
                topic=topic,
                event_id=event.event_id,
                session_id=event.session_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return ProcessingStatus.PERSISTENCE_ERROR

        if inserted is False:
            log_structured(
                self._logger,
                logging.INFO,
                "event_duplicate_ignored",
                topic=topic,
                event_id=event.event_id,
                event_timestamp=event.timestamp.isoformat(),
                source=event.source.value,
            )
            return ProcessingStatus.DUPLICATE_IGNORED

        log_structured(
            self._logger,
            logging.INFO,
            "event_persisted",
            topic=topic,
            event_id=event.event_id,
            session_id=event.session_id,
            source=event.source.value,
            category=event.category.value,
        )
        return ProcessingStatus.PERSISTED

    def _decode_payload(
        self,
        topic: str,
        payload: bytes | bytearray | str,
    ) -> str | None:
        if isinstance(payload, str):
            raw_size = len(payload.encode("utf-8"))
            if raw_size > self._max_payload_bytes:
                self._log_discarded(
                    topic=topic,
                    error=(
                        f"Payload excede o limite de {self._max_payload_bytes} bytes "
                        f"({raw_size} bytes)."
                    ),
                    raw_payload=payload,
                    raw_size=raw_size,
                )
                return None
            return payload

        raw_bytes = bytes(payload)
        raw_size = len(raw_bytes)
        if raw_size > self._max_payload_bytes:
            preview = raw_bytes[: self._max_log_payload_chars].decode(
                "utf-8", errors="replace"
            )
            self._log_discarded(
                topic=topic,
                error=(
                    f"Payload excede o limite de {self._max_payload_bytes} bytes "
                    f"({raw_size} bytes)."
                ),
                raw_payload=preview,
                raw_size=raw_size,
                force_truncated=True,
            )
            return None

        try:
            return raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            sample = raw_bytes[: self._max_log_payload_chars]
            self._log_discarded(
                topic=topic,
                error=f"Payload não UTF-8: {exc}",
                raw_payload=repr(sample),
                raw_size=raw_size,
                force_truncated=raw_size > self._max_log_payload_chars,
            )
            return None

    def _process_status_message(self, topic: str, raw_text: str) -> ProcessingStatus:
        try:
            data = json.loads(raw_text, parse_constant=_reject_json_constant)
        except (json.JSONDecodeError, ValueError, RecursionError) as exc:
            self._log_discarded(
                topic=topic,
                error=f"JSON de status inválido: {exc}",
                raw_payload=raw_text,
            )
            return ProcessingStatus.DISCARDED

        if not isinstance(data, dict) or data.get("status") not in VALID_STATUS_VALUES:
            self._log_discarded(
                topic=topic,
                error="Payload de status deve conter {'status': 'online' | 'offline'}",
                raw_payload=raw_text,
            )
            return ProcessingStatus.DISCARDED

        log_structured(
            self._logger,
            logging.INFO,
            "device_status_received",
            topic=topic,
            status=data["status"],
        )
        return ProcessingStatus.STATUS_RECORDED

    def _validate_telemetry_event(
        self,
        topic: str,
        raw_text: str,
    ) -> TelemetryEvent | None:
        try:
            data = json.loads(raw_text, parse_constant=_reject_json_constant)
        except (json.JSONDecodeError, ValueError, RecursionError) as exc:
            self._log_discarded(
                topic=topic,
                error=f"JSON malformado: {exc}",
                raw_payload=raw_text,
            )
            return None

        if not isinstance(data, dict):
            self._log_discarded(
                topic=topic,
                error="Payload JSON deve ser um objeto.",
                raw_payload=raw_text,
            )
            return None

        if _contains_nul_character(data):
            self._log_discarded(
                topic=topic,
                error="Payload contém caractere NUL (\\u0000) incompatível com JSONB.",
                raw_payload=raw_text,
            )
            return None

        # Exige schema_version explícito na entrada MQTT para impedir fallback silencioso do default.
        if "schema_version" not in data:
            self._log_discarded(
                topic=topic,
                error="Campo obrigatório 'schema_version' ausente.",
                raw_payload=raw_text,
            )
            return None

        try:
            return TelemetryEvent.model_validate(data)
        except ValidationError as exc:
            self._log_discarded(
                topic=topic,
                error=str(exc),
                raw_payload=raw_text,
                validation_errors=exc.errors(include_url=False),
            )
            return None

    def _log_discarded(
        self,
        topic: str,
        error: str,
        raw_payload: str,
        validation_errors: list[dict] | None = None,
        raw_size: int | None = None,
        force_truncated: bool = False,
    ) -> None:
        truncated = force_truncated or len(raw_payload) > self._max_log_payload_chars
        logged_payload = (
            raw_payload[: self._max_log_payload_chars] if truncated else raw_payload
        )
        extra: dict[str, Any] = {
            "topic": topic,
            "error": error,
            "raw_payload": logged_payload,
        }
        if truncated:
            extra["raw_payload_truncated"] = True
            extra["raw_payload_size"] = (
                raw_size if raw_size is not None else len(raw_payload)
            )
        if validation_errors is not None:
            extra["validation_errors"] = validation_errors
        log_structured(self._logger, logging.WARNING, "message_discarded", **extra)
