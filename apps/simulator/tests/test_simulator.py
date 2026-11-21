import json
import signal
import threading
from unittest.mock import MagicMock, patch

import paho.mqtt.client as mqtt
import pytest
from schemas import EventCategory, EventSource, TelemetryEvent
from simulator.client import MqttSensorClient
from simulator.config import SimulatorConfig, load_config
from simulator.generator import _poisson_sample, create_visitor_event
from simulator.main import main


@pytest.fixture
def simulator_config() -> SimulatorConfig:
    return SimulatorConfig(
        host="localhost",
        port=1883,
        username="simulator_user",
        password="simulator_pass_dev",
        topic_telemetry="dsm/prod/totem/sensor/contagem",
        topic_status="dsm/prod/totem/sensor/status",
        interval_seconds=5.0,
        rate_per_minute=30.0,
        client_id="test-sim-01",
    )

def test_poisson_sample_zero_or_negative() -> None:
    assert _poisson_sample(0.0) == 0
    assert _poisson_sample(-5.0) == 0


def test_event_formatting_contract() -> None:
    session_id = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
    event = create_visitor_event(
        people_per_minute=60.0,
        interval_seconds=10.0,
        session_id=session_id,
    )

    assert isinstance(event, TelemetryEvent)
    assert event.schema_version == "1.0"
    assert event.source == EventSource.SENSOR_SIMULATOR
    assert event.category == EventCategory.CONTAGEM_ESTANDE
    assert event.session_id == session_id
    assert isinstance(event.payload["visitor_count"], int)
    assert event.payload["visitor_count"] >= 0


def test_config_env_fallback_and_cli_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MQTT_HOST", "mqtt.internal")
    monkeypatch.delenv("MQTT_USERNAME", raising=False)
    monkeypatch.delenv("MQTT_PASSWORD", raising=False)
    monkeypatch.setenv("MQTT_SIMULATOR_USER", "fallback_user")
    monkeypatch.setenv("MQTT_SIMULATOR_PASSWORD", "fallback_pass")
    monkeypatch.setenv("SIMULATOR_RATE", "20")

    cfg = load_config(["--port", "1884", "--interval", "2.0", "--rate", "40"])
    assert cfg.host == "mqtt.internal"
    assert cfg.port == 1884
    assert cfg.username == "fallback_user"
    assert cfg.password == "fallback_pass"
    assert cfg.interval_seconds == 2.0
    assert cfg.rate_per_minute == 40.0


@pytest.mark.parametrize(
    "args",
    [
        ["--port", "0"],
        ["--port", "70000"],
        ["--interval", "0"],
        ["--interval", "-1"],
        ["--rate", "-0.1"],
    ],
)
def test_config_invalid_parameters(args: list[str]) -> None:
    with pytest.raises(ValueError):
        load_config(args)


def test_on_connect_success_with_int_zero(simulator_config: SimulatorConfig) -> None:
    mock_mqtt = MagicMock(spec=mqtt.Client)
    client = MqttSensorClient(simulator_config, mqtt_client=mock_mqtt)
    client._on_connect(mock_mqtt, None, {}, reason_code=0)

    assert client.is_connected is True
    assert client._connected_event.is_set() is True


def test_on_connect_failure_with_nonzero_int_code(simulator_config: SimulatorConfig) -> None:
    mock_mqtt = MagicMock(spec=mqtt.Client)
    client = MqttSensorClient(simulator_config, mqtt_client=mock_mqtt)
    client._on_connect(mock_mqtt, None, {}, reason_code=5)

    assert client.is_connected is False
    assert client._connected_event.is_set() is False


def test_on_connect_with_paho_reason_code_object(simulator_config: SimulatorConfig) -> None:
    mock_mqtt = MagicMock(spec=mqtt.Client)
    client = MqttSensorClient(simulator_config, mqtt_client=mock_mqtt)

    reason_fail = MagicMock(is_failure=True)
    client._on_connect(mock_mqtt, None, {}, reason_code=reason_fail)
    assert client.is_connected is False

    reason_ok = MagicMock(is_failure=False)
    client._on_connect(mock_mqtt, None, {}, reason_code=reason_ok)
    assert client.is_connected is True


def test_lwt_qos1_publish_and_disconnect(simulator_config: SimulatorConfig) -> None:
    mock_mqtt = MagicMock(spec=mqtt.Client)
    mock_mqtt.publish.return_value.rc = mqtt.MQTT_ERR_SUCCESS

    sensor = MqttSensorClient(simulator_config, mqtt_client=mock_mqtt)

    mock_mqtt.username_pw_set.assert_called_once_with("simulator_user", "simulator_pass_dev")
    mock_mqtt.will_set.assert_called_once_with(
        topic="dsm/prod/totem/sensor/status",
        payload=json.dumps({"status": "offline"}),
        qos=1,
        retain=True,
    )

    sensor._on_connect(mock_mqtt, None, {}, 0)
    assert sensor.is_connected is True

    event = create_visitor_event(30.0, 5.0, "6ba7b810-9dad-11d1-80b4-00c04fd430c8")
    assert sensor.publish_event(event) is True

    call_kwargs = mock_mqtt.publish.call_args.kwargs
    assert call_kwargs["topic"] == "dsm/prod/totem/sensor/contagem"
    assert call_kwargs["qos"] == 1

    sensor.disconnect()
    assert sensor.is_connected is False
    mock_mqtt.loop_stop.assert_called_once()
    mock_mqtt.disconnect.assert_called_once()


def test_connect_retry_and_stop_event(simulator_config: SimulatorConfig) -> None:
    mock_mqtt = MagicMock(spec=mqtt.Client)
    stop_event = threading.Event()
    sensor = MqttSensorClient(simulator_config, stop_event=stop_event, mqtt_client=mock_mqtt)

    attempts = 0

    def connect_side_effect(*args, **kwargs) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("Refused")
        sensor._on_connect(mock_mqtt, None, {}, 0)

    mock_mqtt.connect.side_effect = connect_side_effect

    with patch.object(stop_event, "wait", return_value=False) as mock_wait:
        connected = sensor.connect(timeout=0.1)

    assert connected is True
    assert mock_mqtt.connect.call_count == 2
    mock_wait.assert_called_once_with(timeout=3.0)

    sensor._on_disconnect(mock_mqtt, None, {}, 1)
    assert sensor.is_connected is False
    assert (
        sensor.publish_event(
            create_visitor_event(15.0, 5.0, "6ba7b811-9dad-11d1-80b4-00c04fd430c8")
        )
        is False
    )


def test_connect_aborted_on_stop_signal(simulator_config: SimulatorConfig) -> None:
    mock_mqtt = MagicMock(spec=mqtt.Client)
    stop_event = threading.Event()
    stop_event.set()
    sensor = MqttSensorClient(simulator_config, stop_event=stop_event, mqtt_client=mock_mqtt)

    assert sensor.connect(timeout=0.1) is False


def test_main_graceful_shutdown_on_signal() -> None:
    handlers: dict[int, object] = {}

    def fake_signal(sig, handler) -> None:
        handlers[sig] = handler

    with (
        patch("simulator.main.signal.signal", side_effect=fake_signal),
        patch("simulator.main.MqttSensorClient") as mock_client_cls,
    ):
        mock_instance = mock_client_cls.return_value
        mock_instance.connect.return_value = True

        def trigger_sigint(event) -> None:
            handlers[signal.SIGINT](signal.SIGINT, None)

        mock_instance.publish_event.side_effect = trigger_sigint

        exit_code = main(["--interval", "0.01", "--rate", "10"])

    assert exit_code == 0
    mock_instance.connect.assert_called_once()
    mock_instance.publish_event.assert_called_once()
    mock_instance.disconnect.assert_called_once()


def test_main_returns_error_when_connection_fails() -> None:
    with (
        patch("simulator.main.signal.signal"),
        patch("simulator.main.MqttSensorClient") as mock_client_cls,
    ):
        mock_instance = mock_client_cls.return_value
        mock_instance.connect.return_value = False

        exit_code = main(["--interval", "0.01"])

    assert exit_code == 1
    mock_instance.disconnect.assert_called_once()