import os
import socket
import subprocess
import sys
import uuid
from datetime import UTC, datetime

import paho.mqtt.client as mqtt
import pytest
from paho.mqtt.enums import CallbackAPIVersion
from schemas import EventCategory, EventSource, TelemetryEvent
from simulator.client import MqttSensorClient
from simulator.config import SimulatorConfig
from simulator.generator import create_visitor_event
from simulator.verifier import MqttComplianceMonitor

BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))

APP_USER = os.getenv("MQTT_APP_USER", "app_user")
APP_PASS = os.getenv("MQTT_APP_PASSWORD", "app_pass_dev")

SIMULATOR_USER = os.getenv("MQTT_SIMULATOR_USER", "simulator_user")
SIMULATOR_PASS = os.getenv("MQTT_SIMULATOR_PASSWORD", "simulator_pass_dev")

INGESTOR_USER = os.getenv("MQTT_INGESTOR_USER", "ingestor_user")
INGESTOR_PASS = os.getenv("MQTT_INGESTOR_PASSWORD", "ingestor_pass_dev")


def _is_broker_running() -> bool:
    try:
        with socket.create_connection((BROKER_HOST, BROKER_PORT), timeout=1.0):
            return True
    except OSError:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _is_broker_running(),
        reason=(
            f"Broker MQTT não está em execução em {BROKER_HOST}:{BROKER_PORT} "
            "(inicie com make up-infra)"
        ),
    ),
]


def _publish_as_app(topic: str, payload: str, qos: int = 1) -> None:
    client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
    client.username_pw_set(APP_USER, APP_PASS)
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=10)
    client.loop_start()
    try:
        info = client.publish(topic, payload, qos=qos)
        info.wait_for_publish(timeout=5.0)
        assert info.rc == mqtt.MQTT_ERR_SUCCESS
    finally:
        client.disconnect()
        client.loop_stop()


def test_wildcard_subscription_validates_multiple_sources_and_qos1():
    sim_session_id = str(uuid.uuid4())
    app_event_id = str(uuid.uuid4())

    with MqttComplianceMonitor(
        host=BROKER_HOST,
        port=BROKER_PORT,
        username=INGESTOR_USER,
        password=INGESTOR_PASS,
        qos=1,
    ) as monitor:
        sim_config = SimulatorConfig(
            host=BROKER_HOST,
            port=BROKER_PORT,
            username=SIMULATOR_USER,
            password=SIMULATOR_PASS,
            topic_telemetry="dsm/prod/totem/sensor/contagem",
            topic_status="dsm/prod/totem/sensor/status",
            interval_seconds=1.0,
            rate_per_minute=20.0,
            client_id=f"integration-sim-{uuid.uuid4().hex[:8]}",
        )
        sim_client = MqttSensorClient(sim_config)
        assert sim_client.connect(timeout=5.0)
        try:
            sim_event = create_visitor_event(
                people_per_minute=20.0,
                interval_seconds=1.0,
                session_id=sim_session_id,
            )
            assert sim_client.publish_event(sim_event)
        finally:
            sim_client.disconnect()

        app_event = TelemetryEvent(
            timestamp=datetime.now(UTC),
            event_id=app_event_id,
            session_id=str(uuid.uuid4()),
            source=EventSource.APP_MOBILE,
            category=EventCategory.INTERACAO_TELA,
            payload={"screen_name": "cursos", "action": "view"},
        )
        _publish_as_app(
            topic="dsm/prod/app/interacao/tela",
            payload=app_event.model_dump_json(),
            qos=1,
        )

        received = monitor.verifier.wait_for(
            lambda v: (
                v.has_required_sources()
                and any(r.event.event_id == app_event_id for r in v.valid_records)
                and any(r.event.session_id == sim_session_id for r in v.valid_records)
            ),
            timeout=10.0,
        )
        assert received, "Timeout aguardando mensagens de SENSOR_SIMULATOR e APP_*"

        summary = monitor.verifier.log_summary()
        assert summary["anomaly_count"] == 0
        assert summary["valid_telemetry_count"] >= 2
        assert summary["has_sensor_simulator"] is True
        assert summary["has_app_source"] is True

        matching_records = [
            record
            for record in monitor.verifier.valid_records
            if record.event.event_id == app_event_id
            or record.event.session_id == sim_session_id
        ]
        assert len(matching_records) >= 2
        assert all(record.qos == 1 for record in matching_records)


def test_schema_anomaly_detection_on_live_broker():
    invalid_marker = f"invalid-{uuid.uuid4().hex[:8]}"

    with MqttComplianceMonitor(
        host=BROKER_HOST,
        port=BROKER_PORT,
        username=INGESTOR_USER,
        password=INGESTOR_PASS,
        qos=1,
    ) as monitor:
        _publish_as_app(
            topic="dsm/prod/app/interacao/tela",
            payload=f'{{"schema_version": "9.9", "marker": "{invalid_marker}"}}',
            qos=1,
        )

        detected = monitor.verifier.wait_for(
            lambda v: any(invalid_marker in item.raw_payload for item in v.anomalies),
            timeout=5.0,
        )
        assert detected, "Anomalia de schema não foi detectada no broker"

        summary = monitor.verifier.log_summary()
        assert summary["anomaly_count"] >= 1
        assert any(
            item["topic"] == "dsm/prod/app/interacao/tela"
            for item in summary["anomalies"]
        )


def test_simulator_lwt_delivered_on_forced_termination():
    client_id = f"integration-lwt-{uuid.uuid4().hex[:8]}"

    with MqttComplianceMonitor(
        host=BROKER_HOST,
        port=BROKER_PORT,
        username=INGESTOR_USER,
        password=INGESTOR_PASS,
        qos=1,
    ) as monitor:
        initial_status_count = len(monitor.verifier.status_messages)
        initial_valid_count = monitor.verifier.valid_count

        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "simulator.main",
                "--host",
                BROKER_HOST,
                "--port",
                str(BROKER_PORT),
                "--username",
                SIMULATOR_USER,
                "--password",
                SIMULATOR_PASS,
                "--interval",
                "1",
                "--rate",
                "30",
                "--client-id",
                client_id,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            sim_ready = monitor.verifier.wait_for(
                lambda v: (
                    any(
                        msg.topic == "dsm/prod/totem/sensor/status"
                        and msg.status == "online"
                        for msg in v.status_messages[initial_status_count:]
                    )
                    and any(
                        rec.event.source == EventSource.SENSOR_SIMULATOR
                        for rec in v.valid_records[initial_valid_count:]
                    )
                ),
                timeout=10.0,
            )
            if not sim_ready:
                proc.kill()
                _, stderr_output = proc.communicate(timeout=5.0)
                pytest.fail(
                    "Simulador não publicou status online e telemetria inicial"
                    f" (stderr={stderr_output.decode('utf-8', errors='replace')!r})"
                )

            status_count_before_kill = len(monitor.verifier.status_messages)

            # Encerramento forçado (SIGKILL) sem pacote MQTT DISCONNECT para disparar o LWT no broker
            proc.kill()
            proc.communicate(timeout=5.0)

            lwt_received = monitor.verifier.wait_for(
                lambda v: any(
                    msg.topic == "dsm/prod/totem/sensor/status"
                    and msg.status == "offline"
                    and msg.qos == 1
                    for msg in v.status_messages[status_count_before_kill:]
                ),
                timeout=10.0,
            )
            assert lwt_received, (
                "Mensagem LWT {'status': 'offline'} com QoS 1 não recebida após SIGKILL"
            )
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.communicate(timeout=5.0)
            if proc.stdout is not None and not proc.stdout.closed:
                proc.stdout.close()
            if proc.stderr is not None and not proc.stderr.closed:
                proc.stderr.close()
