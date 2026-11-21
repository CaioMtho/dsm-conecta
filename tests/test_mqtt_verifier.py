import json
import logging
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from schemas import EventCategory, EventSource, TelemetryEvent
from simulator.verifier import MqttComplianceMonitor, MqttComplianceVerifier, main

DEFAULT_EVENT_ID = "550e8400-e29b-41d4-a716-446655440000"
DEFAULT_SESSION_ID = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"


def _make_event(
    source: EventSource,
    category: EventCategory,
    event_id: str = DEFAULT_EVENT_ID,
    session_id: str = DEFAULT_SESSION_ID,
    payload: dict | None = None,
) -> str:
    event = TelemetryEvent(
        timestamp=datetime(2026, 10, 20, 12, 0, 0, tzinfo=UTC),
        event_id=event_id,
        session_id=session_id,
        source=source,
        category=category,
        payload=payload or {"screen": "home"},
    )
    return event.model_dump_json()


def test_verifier_validates_multiple_sources_and_tracks_qos():
    verifier = MqttComplianceVerifier()

    sim_payload = _make_event(
        source=EventSource.SENSOR_SIMULATOR,
        category=EventCategory.CONTAGEM_ESTANDE,
        event_id="550e8400-e29b-41d4-a716-446655440001",
        payload={"visitor_count": 3},
    )
    app_payload = _make_event(
        source=EventSource.APP_MOBILE,
        category=EventCategory.INTERACAO_TELA,
        event_id="550e8400-e29b-41d4-a716-446655440002",
        payload={"screen_name": "cursos"},
    )

    assert verifier.process_message(
        topic="dsm/prod/totem/sensor/contagem",
        payload=sim_payload.encode(),
        qos=1,
    )
    assert verifier.has_required_sources() is False

    assert verifier.process_message(
        topic="dsm/prod/app/interacao/tela",
        payload=app_payload.encode(),
        qos=1,
    )

    assert verifier.valid_count == 2
    assert verifier.anomaly_count == 0
    assert verifier.has_required_sources() is True
    assert verifier.sources_seen == {EventSource.SENSOR_SIMULATOR, EventSource.APP_MOBILE}
    assert verifier.counts_by_source == {"sensor_simulator": 1, "app_mobile": 1}
    assert all(record.qos == 1 for record in verifier.valid_records)


def test_verifier_detects_invalid_json_and_schema_anomalies():
    verifier = MqttComplianceVerifier()

    assert not verifier.process_message(
        topic="dsm/prod/app/interacao/tela",
        payload=b"{invalid-json",
        qos=1,
    )
    assert not verifier.process_message(
        topic="dsm/prod/app/interacao/tela",
        payload=json.dumps({"schema_version": "2.0", "event_id": "x"}).encode(),
        qos=0,
    )

    assert verifier.valid_count == 0
    assert verifier.anomaly_count == 2
    assert verifier.anomalies[0].topic == "dsm/prod/app/interacao/tela"
    assert verifier.anomalies[1].topic == "dsm/prod/app/interacao/tela"


def test_verifier_handles_status_lwt_messages_separately():
    verifier = MqttComplianceVerifier()

    assert verifier.process_message(
        topic="dsm/prod/totem/sensor/status",
        payload=json.dumps({"status": "online"}).encode(),
        qos=1,
        retain=True,
    )
    assert verifier.process_message(
        topic="dsm/prod/totem/sensor/status",
        payload=json.dumps({"status": "offline"}).encode(),
        qos=1,
        retain=True,
    )

    assert verifier.valid_count == 0
    assert verifier.anomaly_count == 0
    assert [msg.status for msg in verifier.status_messages] == ["online", "offline"]
    assert all(msg.qos == 1 and msg.retain for msg in verifier.status_messages)


def test_verifier_flags_malformed_status_payload_as_anomaly():
    verifier = MqttComplianceVerifier()

    assert not verifier.process_message(
        topic="dsm/prod/totem/sensor/status",
        payload=json.dumps({"state": "unknown"}).encode(),
        qos=1,
    )

    assert verifier.anomaly_count == 1
    assert len(verifier.status_messages) == 0


def test_verifier_emits_structured_json_summary_log(caplog):
    logger = logging.getLogger("test.mqtt.verifier")
    verifier = MqttComplianceVerifier(logger=logger)

    verifier.process_message(
        topic="dsm/prod/totem/sensor/contagem",
        payload=_make_event(
            source=EventSource.SENSOR_SIMULATOR,
            category=EventCategory.CONTAGEM_ESTANDE,
        ).encode(),
        qos=1,
    )
    verifier.process_message(
        topic="dsm/prod/app/interacao/tela",
        payload=b"not-json",
        qos=1,
    )

    with caplog.at_level(logging.INFO, logger=logger.name):
        summary = verifier.log_summary()

    assert summary["valid_telemetry_count"] == 1
    assert summary["anomaly_count"] == 1
    assert summary["sources"] == {"sensor_simulator": 1}
    assert len(summary["anomalies"]) == 1

    summary_records = [
        json.loads(record.message)
        for record in caplog.records
        if "mqtt_compliance_summary" in record.message
    ]
    assert len(summary_records) == 1
    assert summary_records[0]["valid_telemetry_count"] == 1
    assert summary_records[0]["anomaly_count"] == 1


def test_verifier_handles_non_utf8_and_invalid_status_json():
    verifier = MqttComplianceVerifier()

    assert not verifier.process_message("dsm/prod/app/interacao/tela", b"\xff\xfe", qos=1)
    assert not verifier.process_message("dsm/prod/totem/sensor/status", b"{bad", qos=1)
    assert verifier.anomaly_count == 2


def test_verifier_wait_for_returns_true_and_false_on_timeout():
    verifier = MqttComplianceVerifier()
    assert verifier.wait_for(lambda v: v.valid_count > 0, timeout=0.05) is False

    verifier.process_message(
        topic="dsm/prod/totem/sensor/contagem",
        payload=_make_event(
            source=EventSource.SENSOR_SIMULATOR,
            category=EventCategory.CONTAGEM_ESTANDE,
        ).encode(),
        qos=1,
    )
    assert verifier.wait_for(lambda v: v.valid_count == 1, timeout=0.05) is True


def test_monitor_callbacks_and_cli_exit_codes(monkeypatch):
    monitor = MqttComplianceMonitor(
        host="localhost",
        port=1883,
        username="ingestor_user",
        password="secret",
    )
    fake_client = MagicMock()
    monitor._on_connect(fake_client, None, None, 0)
    fake_client.subscribe.assert_called_once_with("dsm/prod/#", qos=1)
    monitor._on_subscribe(fake_client, None, 1, [])

    fake_msg = MagicMock()
    fake_msg.topic = "dsm/prod/app/interacao/tela"
    fake_msg.payload = _make_event(
        source=EventSource.APP_WEB,
        category=EventCategory.INTERACAO_TELA,
    ).encode()
    fake_msg.qos = 1
    fake_msg.retain = False
    monitor._on_message(fake_client, None, fake_msg)

    assert monitor.verifier.valid_count == 1

    class _FakeMonitor:
        def __init__(self, *args, **kwargs):
            self.verifier = monitor.verifier

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    monkeypatch.setattr("simulator.verifier.MqttComplianceMonitor", _FakeMonitor)
    monkeypatch.setattr("simulator.verifier.time.sleep", lambda _: None)

    assert main(["--duration", "0"]) == 0
    assert main(["--duration", "0", "--require-multi-source"]) == 1

    monitor.verifier.process_message("dsm/prod/app/interacao/tela", b"{bad", qos=1)
    assert main(["--duration", "0"]) == 1


def test_monitor_init_preserves_explicit_empty_credentials(monkeypatch):
    monkeypatch.setenv("MQTT_INGESTOR_USER", "env_user")
    monkeypatch.setenv("MQTT_INGESTOR_PASSWORD", "env_pass")

    monitor = MqttComplianceMonitor(username="", password="")
    assert monitor.username == ""
    assert monitor.password == ""


def test_monitor_stop_disconnects_before_stopping_loop():
    monitor = MqttComplianceMonitor(host="localhost", port=1883)
    call_order: list[str] = []
    fake_client = MagicMock()
    fake_client.disconnect.side_effect = lambda: call_order.append("disconnect")
    fake_client.loop_stop.side_effect = lambda: call_order.append("loop_stop")
    monitor._client = fake_client

    monitor.stop()
    assert call_order == ["disconnect", "loop_stop"]


def test_monitor_start_raises_on_subscribe_acl_failure():
    monitor = MqttComplianceMonitor(host="localhost", port=1883)
    fake_client = MagicMock()

    def _simulate_loop_start():
        monitor._on_connect(fake_client, None, None, 0)
        monitor._on_subscribe(
            fake_client,
            None,
            1,
            [SimpleNamespace(is_failure=True, value=128)],
        )

    fake_client.loop_start.side_effect = _simulate_loop_start
    monitor._client = fake_client

    with pytest.raises(PermissionError, match="assinar"):
        monitor.start(timeout=1.0)


def test_monitor_start_raises_on_connect_error_and_timeout():
    monitor = MqttComplianceMonitor(host="localhost", port=1883)
    fake_client = MagicMock()
    fake_client.loop_start.side_effect = lambda: monitor._on_connect(
        fake_client, None, None, 5
    )
    monitor._client = fake_client

    with pytest.raises(ConnectionError, match="autenticação"):
        monitor.start(timeout=1.0)

    monitor_timeout = MqttComplianceMonitor(host="localhost", port=1883)
    monitor_timeout._client = MagicMock()
    with pytest.raises(TimeoutError, match="conectar"):
        monitor_timeout.start(timeout=0.02)


def test_cli_handles_keyboard_interrupt_and_logs_summary(monkeypatch):
    verifier = MqttComplianceVerifier()
    verifier.process_message(
        topic="dsm/prod/totem/sensor/contagem",
        payload=_make_event(
            source=EventSource.SENSOR_SIMULATOR,
            category=EventCategory.CONTAGEM_ESTANDE,
        ).encode(),
        qos=1,
    )

    class _FakeMonitor:
        def __init__(self, *args, **kwargs):
            self.verifier = verifier

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    def _raise_interrupt(_duration):
        raise KeyboardInterrupt

    monkeypatch.setattr("simulator.verifier.MqttComplianceMonitor", _FakeMonitor)
    monkeypatch.setattr("simulator.verifier.time.sleep", _raise_interrupt)

    assert main(["--duration", "5"]) == 0


