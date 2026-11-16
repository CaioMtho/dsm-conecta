from unittest.mock import MagicMock

import pytest
from simulator.client import (
    MqttSensorClient,  # ajuste o import conforme sua nova estrutura
)
from simulator.config import SimulatorConfig


@pytest.fixture
def simulator_config() -> SimulatorConfig:
    return SimulatorConfig(
        host="localhost",
        port=1883,
        username="simulator_user",
        password="simulator_pass_dev",
        interval_seconds=5.0,
        rate_per_minute=10.0,
    )



def test_on_connect_success_with_int_zero(simulator_config):
    client = MqttSensorClient(simulator_config)
    client._on_connect(MagicMock(), None, {}, reason_code=0)

    assert client.is_connected is True
    assert client._connected_event.is_set() is True


def test_on_connect_failure_with_nonzero_int_code(simulator_config):
    client = MqttSensorClient(simulator_config)
    # Código 5 no MQTT v3.1.1 = Not authorized
    client._on_connect(MagicMock(), None, {}, reason_code=5)

    assert client.is_connected is False
    assert client._connected_event.is_set() is False


def test_on_connect_with_paho_reason_code_object(simulator_config):
    client = MqttSensorClient(simulator_config)

    reason_fail = MagicMock(is_failure=True)
    client._on_connect(MagicMock(), None, {}, reason_code=reason_fail)
    assert client.is_connected is False

    reason_ok = MagicMock(is_failure=False)
    client._on_connect(MagicMock(), None, {}, reason_code=reason_ok)
    assert client.is_connected is True
