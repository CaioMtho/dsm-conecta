import json
from unittest.mock import MagicMock, patch

import paho.mqtt.client as mqtt
import pytest
from schemas import EventCategory, EventSource, TelemetryEvent

from src.client import MqttSensorClient
from src.config import SimulatorConfig, load_config
from src.generator import create_visitor_event


@pytest.fixture
def sample_config() -> SimulatorConfig:
    return SimulatorConfig(
        broker_host="localhost",
        broker_port=1883,
        username="sim_user",
        password="sim_password",
        topic_telemetry="dsm/prod/totem/sensor/contagem",
        topic_status="dsm/prod/totem/sensor/status",
        interval_seconds=5.0,
        people_per_minute=30.0,
        client_id="test-sim-01",
    )


def test_event_formatting_contract() -> None:
    event = create_visitor_event(
        people_per_minute=60.0,
        interval_seconds=10.0,
        session_id="session-test-01",
    )

    assert isinstance(event, TelemetryEvent)
    assert event.schema_version == "1.0"
    assert event.source == EventSource.SENSOR_SIMULATOR
    assert event.category == EventCategory.CONTAGEM_ESTANDE
    assert event.session_id == "session-test-01"
    assert isinstance(event.payload["visitor_count"], int)
    assert event.payload["visitor_count"] >= 0


def test_lwt_and_qos1_publish(sample_config: SimulatorConfig) -> None:
    mock_mqtt = MagicMock(spec=mqtt.Client)
    mock_mqtt.publish.return_value.rc = mqtt.MQTT_ERR_SUCCESS

    sensor = MqttSensorClient(sample_config, mqtt_client=mock_mqtt)

    mock_mqtt.username_pw_set.assert_called_once_with("sim_user", "sim_password")
    mock_mqtt.will_set.assert_called_once_with(
        topic="dsm/prod/totem/sensor/status",
        payload=json.dumps({"status": "offline"}),
        qos=1,
        retain=True,
    )

    sensor._on_connect(mock_mqtt, None, None, 0)
    assert sensor.is_connected is True

    event = create_visitor_event(30.0, 5.0, "session-1")
    assert sensor.publish_event(event) is True

    call_kwargs = mock_mqtt.publish.call_args.kwargs
    assert call_kwargs["topic"] == "dsm/prod/totem/sensor/contagem"
    assert call_kwargs["qos"] == 1

    body = json.loads(call_kwargs["payload"])
    assert body["source"] == "sensor_simulator"
    assert body["category"] == "contagem_estande"


def test_reconnection_on_network_failure(sample_config: SimulatorConfig) -> None:
    mock_mqtt = MagicMock(spec=mqtt.Client)
    mock_mqtt.connect.side_effect = [OSError("Refused"), OSError("Timeout"), None]

    sensor = MqttSensorClient(sample_config, mqtt_client=mock_mqtt)

    with patch("time.sleep") as mock_sleep:
        sensor.connect()

    assert mock_mqtt.connect.call_count == 3
    assert mock_sleep.call_count == 2
    mock_mqtt.loop_start.assert_called_once()

    sensor._on_connect(mock_mqtt, None, None, 0)
    assert sensor.is_connected is True

    sensor._on_disconnect(mock_mqtt, None, None, 1)
    assert sensor.is_connected is False

    event = create_visitor_event(15.0, 5.0, "session-2")
    assert sensor.publish_event(event) is False


def test_config_env_and_cli_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MQTT_HOST", "mqtt.internal")
    monkeypatch.setenv("SIMULATOR_PEOPLE_PER_MINUTE", "20")

    cfg = load_config(["--port", "1884", "--interval", "2.0", "--rate", "40"])
    assert cfg.broker_host == "mqtt.internal"
    assert cfg.broker_port == 1884
    assert cfg.interval_seconds == 2.0
    assert cfg.people_per_minute == 40.0
