import argparse
import json
import logging
import os
import sys
import threading
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Self

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from pydantic import ValidationError
from schemas import EventSource, TelemetryEvent

APP_SOURCES: frozenset[EventSource] = frozenset(
    {
        EventSource.APP_MOBILE,
        EventSource.APP_WEB,
        EventSource.APP_DESKTOP,
    }
)
VALID_STATUS_VALUES: frozenset[str] = frozenset({"online", "offline"})
DEFAULT_TOPIC_WILDCARD = "dsm/prod/#"


@dataclass(frozen=True)
class TelemetryRecord:
    topic: str
    event: TelemetryEvent
    qos: int
    retain: bool
    received_at: datetime


@dataclass(frozen=True)
class StatusMessage:
    topic: str
    status: str
    qos: int
    retain: bool
    raw_payload: str
    received_at: datetime


@dataclass(frozen=True)
class SchemaAnomaly:
    topic: str
    reason: str
    raw_payload: str
    qos: int
    received_at: datetime


class MqttComplianceVerifier:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger(__name__)
        self._condition = threading.Condition()
        self._valid_records: list[TelemetryRecord] = []
        self._status_messages: list[StatusMessage] = []
        self._anomalies: list[SchemaAnomaly] = []

    def process_message(
        self,
        topic: str,
        payload: bytes,
        qos: int = 0,
        retain: bool = False,
    ) -> bool:
        now = datetime.now(UTC)
        try:
            raw_text = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            self._record_anomaly(topic, f"Payload não UTF-8: {exc}", repr(payload), qos, now)
            return False

        if topic.endswith("/status"):
            return self._process_status_message(topic, raw_text, qos, retain, now)

        try:
            event = TelemetryEvent.model_validate_json(raw_text)
        except ValidationError as exc:
            self._record_anomaly(topic, str(exc), raw_text, qos, now)
            return False

        record = TelemetryRecord(
            topic=topic,
            event=event,
            qos=qos,
            retain=retain,
            received_at=now,
        )
        with self._condition:
            self._valid_records.append(record)
            self._condition.notify_all()

        self._emit_structured_log(
            logging.INFO,
            {
                "event": "mqtt_telemetry_valid",
                "topic": topic,
                "source": event.source.value,
                "category": event.category.value,
                "event_id": event.event_id,
                "qos": qos,
            },
        )
        return True

    def _process_status_message(
        self,
        topic: str,
        raw_text: str,
        qos: int,
        retain: bool,
        received_at: datetime,
    ) -> bool:
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            self._record_anomaly(topic, f"JSON de status inválido: {exc}", raw_text, qos, received_at)
            return False

        if not isinstance(data, dict) or data.get("status") not in VALID_STATUS_VALUES:
            self._record_anomaly(
                topic,
                "Payload de status deve conter {'status': 'online' | 'offline'}",
                raw_text,
                qos,
                received_at,
            )
            return False

        message = StatusMessage(
            topic=topic,
            status=data["status"],
            qos=qos,
            retain=retain,
            raw_payload=raw_text,
            received_at=received_at,
        )
        with self._condition:
            self._status_messages.append(message)
            self._condition.notify_all()

        self._emit_structured_log(
            logging.INFO,
            {
                "event": "mqtt_status_received",
                "topic": topic,
                "status": message.status,
                "qos": qos,
                "retain": retain,
            },
        )
        return True

    def _record_anomaly(
        self,
        topic: str,
        reason: str,
        raw_payload: str,
        qos: int,
        received_at: datetime,
    ) -> None:
        anomaly = SchemaAnomaly(
            topic=topic,
            reason=reason,
            raw_payload=raw_payload,
            qos=qos,
            received_at=received_at,
        )
        with self._condition:
            self._anomalies.append(anomaly)
            self._condition.notify_all()

        self._emit_structured_log(
            logging.WARNING,
            {
                "event": "mqtt_schema_anomaly",
                "topic": topic,
                "reason": reason,
                "qos": qos,
            },
        )

    def _emit_structured_log(self, level: int, payload: dict[str, Any]) -> None:
        self._logger.log(level, json.dumps(payload, ensure_ascii=False))

    def wait_for(
        self,
        predicate: Callable[["MqttComplianceVerifier"], bool],
        timeout: float = 10.0,
    ) -> bool:
        deadline = time.monotonic() + timeout
        with self._condition:
            while not predicate(self):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._condition.wait(timeout=remaining)
            return True

    @property
    def valid_records(self) -> list[TelemetryRecord]:
        with self._condition:
            return list(self._valid_records)

    @property
    def status_messages(self) -> list[StatusMessage]:
        with self._condition:
            return list(self._status_messages)

    @property
    def anomalies(self) -> list[SchemaAnomaly]:
        with self._condition:
            return list(self._anomalies)

    @property
    def valid_count(self) -> int:
        with self._condition:
            return len(self._valid_records)

    @property
    def anomaly_count(self) -> int:
        with self._condition:
            return len(self._anomalies)

    @property
    def sources_seen(self) -> set[EventSource]:
        with self._condition:
            return {record.event.source for record in self._valid_records}

    @property
    def counts_by_source(self) -> dict[str, int]:
        with self._condition:
            return dict(Counter(record.event.source.value for record in self._valid_records))

    def has_required_sources(self) -> bool:
        sources = self.sources_seen
        return EventSource.SENSOR_SIMULATOR in sources and bool(sources & APP_SOURCES)

    def build_summary(self) -> dict[str, Any]:
        with self._condition:
            sources_counter = Counter(
                record.event.source.value for record in self._valid_records
            )
            topics_counter = Counter(record.topic for record in self._valid_records)
            sources_set = {record.event.source for record in self._valid_records}
            return {
                "event": "mqtt_compliance_summary",
                "total_messages": (
                    len(self._valid_records)
                    + len(self._status_messages)
                    + len(self._anomalies)
                ),
                "valid_telemetry_count": len(self._valid_records),
                "status_messages_count": len(self._status_messages),
                "anomaly_count": len(self._anomalies),
                "sources": dict(sources_counter),
                "topics": dict(topics_counter),
                "has_sensor_simulator": EventSource.SENSOR_SIMULATOR in sources_set,
                "has_app_source": bool(sources_set & APP_SOURCES),
                "anomalies": [
                    {
                        "topic": item.topic,
                        "reason": item.reason,
                        "qos": item.qos,
                    }
                    for item in self._anomalies
                ],
            }

    def log_summary(self) -> dict[str, Any]:
        summary = self.build_summary()
        self._emit_structured_log(logging.INFO, summary)
        return summary


class MqttComplianceMonitor:
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        topic: str = DEFAULT_TOPIC_WILDCARD,
        qos: int = 1,
        verifier: MqttComplianceVerifier | None = None,
    ) -> None:
        self.host = host or os.getenv("MQTT_BROKER_HOST", "localhost")
        self.port = port or int(os.getenv("MQTT_BROKER_PORT", "1883"))
        self.username = username or os.getenv("MQTT_INGESTOR_USER", "ingestor_user")
        self.password = password or os.getenv("MQTT_INGESTOR_PASSWORD", "ingestor_pass_dev")
        self.topic = topic
        self.qos = qos
        self.verifier = verifier or MqttComplianceVerifier()

        self._connected_event = threading.Event()
        self._subscribed_event = threading.Event()
        self._connect_error: Any = None

        self._client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
        if self.username:
            self._client.username_pw_set(self.username, self.password)
        self._client.on_connect = self._on_connect
        self._client.on_subscribe = self._on_subscribe
        self._client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        is_success = reason_code == 0 or (
            hasattr(reason_code, "is_failure") and not reason_code.is_failure
        )
        if is_success:
            self._connected_event.set()
            client.subscribe(self.topic, qos=self.qos)
        else:
            self._connect_error = reason_code
            self._connected_event.set()

    def _on_subscribe(
        self, client, userdata, mid, reason_code_list, properties=None
    ) -> None:
        self._subscribed_event.set()

    def _on_message(self, client, userdata, msg) -> None:
        self.verifier.process_message(
            topic=msg.topic,
            payload=msg.payload,
            qos=msg.qos,
            retain=bool(msg.retain),
        )

    def start(self, timeout: float = 5.0) -> None:
        self._connected_event.clear()
        self._subscribed_event.clear()
        self._connect_error = None
        self._client.connect(self.host, self.port, keepalive=30)
        self._client.loop_start()

        if not self._connected_event.wait(timeout=timeout):
            self.stop()
            raise TimeoutError(
                f"Timeout ao conectar no broker MQTT em {self.host}:{self.port}"
            )
        if self._connect_error is not None:
            self.stop()
            raise ConnectionError(
                f"Falha de autenticação/conexão no broker MQTT: {self._connect_error}"
            )
        if not self._subscribed_event.wait(timeout=timeout):
            self.stop()
            raise TimeoutError(f"Timeout ao assinar tópico {self.topic}")

    def stop(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Monitor de conformidade de protocolo e schemas MQTT (dsm/prod/#)"
    )
    parser.add_argument("--host", default=os.getenv("MQTT_BROKER_HOST", "localhost"))
    parser.add_argument(
        "--port", type=int, default=int(os.getenv("MQTT_BROKER_PORT", "1883"))
    )
    parser.add_argument(
        "--username", default=os.getenv("MQTT_INGESTOR_USER", "ingestor_user")
    )
    parser.add_argument(
        "--password", default=os.getenv("MQTT_INGESTOR_PASSWORD", "ingestor_pass_dev")
    )
    parser.add_argument("--topic", default=DEFAULT_TOPIC_WILDCARD)
    parser.add_argument("--duration", type=float, default=15.0)
    parser.add_argument("--require-multi-source", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    monitor = MqttComplianceMonitor(
        host=args.host,
        port=args.port,
        username=args.username,
        password=args.password,
        topic=args.topic,
        qos=1,
    )

    with monitor:
        time.sleep(args.duration)

    summary = monitor.verifier.log_summary()
    if summary["anomaly_count"] > 0:
        return 1
    if args.require_multi_source and not monitor.verifier.has_required_sources():
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
