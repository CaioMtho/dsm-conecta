import json
import logging
from enum import Enum

import asyncpg
from pydantic import ValidationError
from schemas import TelemetryEvent

from ingestor.logging_config import log_structured
from ingestor.repository import EventRepository

VALID_STATUS_VALUES: frozenset[str] = frozenset({"online", "offline"})
PERSISTENCE_EXCEPTIONS = (
    asyncpg.PostgresError,
    asyncpg.InterfaceError,
    OSError,
    TimeoutError,
    RuntimeError,
)


class ProcessingStatus(str, Enum):
    PERSISTED = "persisted"
    STATUS_RECORDED = "status_recorded"
    DISCARDED = "discarded"
    PERSISTENCE_ERROR = "persistence_error"


class MessageProcessor:
    def __init__(
        self,
        repository: EventRepository,
        logger: logging.Logger | None = None,
    ) -> None:
        self._repository = repository
        self._logger = logger or logging.getLogger("ingestor")

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
            await self._repository.insert_event(event)
        except PERSISTENCE_EXCEPTIONS as exc:
            log_structured(
                self._logger,
                logging.ERROR,
                "persistence_failed",
                topic=topic,
                event_id=event.event_id,
                session_id=event.session_id,
                error=str(exc),
            )
            return ProcessingStatus.PERSISTENCE_ERROR

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
            return payload
        try:
            return bytes(payload).decode("utf-8")
        except UnicodeDecodeError as exc:
            self._log_discarded(
                topic=topic,
                error=f"Payload não UTF-8: {exc}",
                raw_payload=repr(bytes(payload)),
            )
            return None

    def _process_status_message(self, topic: str, raw_text: str) -> ProcessingStatus:
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
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
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
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
    ) -> None:
        extra: dict = {
            "topic": topic,
            "error": error,
            "raw_payload": raw_payload,
        }
        if validation_errors is not None:
            extra["validation_errors"] = validation_errors
        log_structured(self._logger, logging.WARNING, "message_discarded", **extra)
