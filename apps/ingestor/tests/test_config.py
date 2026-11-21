import pytest
from ingestor.config import IngestorConfig


def test_config_defaults():
    cfg = IngestorConfig.from_env({})

    assert cfg.mqtt_host == "localhost"
    assert cfg.mqtt_port == 1883
    assert cfg.mqtt_username == "ingestor_user"
    assert cfg.mqtt_password == "ingestor_pass_dev"
    assert cfg.mqtt_topic == "dsm/prod/#"
    assert cfg.mqtt_qos == 1
    assert cfg.mqtt_keepalive == 60
    assert cfg.database_url == "postgresql://dsm_user:dsm_password@localhost:5432/dsm_conecta"
    assert cfg.db_pool_min_size == 2
    assert cfg.db_pool_max_size == 10
    assert cfg.db_command_timeout == 10.0
    assert cfg.reconnect_initial_delay == 1.0
    assert cfg.reconnect_max_delay == 30.0
    assert cfg.log_level == "INFO"


def test_config_from_docker_compose_env():
    env = {
        "DATABASE_URL": "postgresql://prod_user:secret@db:5432/prod_db",
        "MQTT_BROKER_HOST": "broker",
        "MQTT_BROKER_PORT": "1884",
        "MQTT_BROKER_USER": "ingestor_user",
        "MQTT_BROKER_PASSWORD": "strong_password",
        "MQTT_TOPIC": "dsm/prod/#",
        "MQTT_QOS": "1",
        "MQTT_CLIENT_ID": "ingestor-node-1",
        "DB_POOL_MIN_SIZE": "3",
        "DB_POOL_MAX_SIZE": "15",
        "DB_COMMAND_TIMEOUT": "15.5",
        "MQTT_RECONNECT_INITIAL_DELAY": "0.5",
        "MQTT_RECONNECT_MAX_DELAY": "20.0",
        "LOG_LEVEL": "debug",
    }

    cfg = IngestorConfig.from_env(env)

    assert cfg.database_url == "postgresql://prod_user:secret@db:5432/prod_db"
    assert cfg.mqtt_host == "broker"
    assert cfg.mqtt_port == 1884
    assert cfg.mqtt_username == "ingestor_user"
    assert cfg.mqtt_password == "strong_password"
    assert cfg.mqtt_client_id == "ingestor-node-1"
    assert cfg.db_pool_min_size == 3
    assert cfg.db_pool_max_size == 15
    assert cfg.db_command_timeout == 15.5
    assert cfg.reconnect_initial_delay == 0.5
    assert cfg.reconnect_max_delay == 20.0
    assert cfg.log_level == "DEBUG"


def test_config_fallback_to_env_example_variables():
    env = {
        "POSTGRES_USER": "custom_pg",
        "POSTGRES_PASSWORD": "custom_pw",
        "POSTGRES_HOST": "timescale.local",
        "POSTGRES_PORT": "5433",
        "POSTGRES_DB": "telemetry_db",
        "MQTT_INGESTOR_USER": "ingestor_alt",
        "MQTT_INGESTOR_PASSWORD": "ingestor_alt_pw",
    }

    cfg = IngestorConfig.from_env(env)

    assert cfg.database_url == "postgresql://custom_pg:custom_pw@timescale.local:5433/telemetry_db"
    assert cfg.mqtt_username == "ingestor_alt"
    assert cfg.mqtt_password == "ingestor_alt_pw"


@pytest.mark.parametrize(
    "env_override",
    [
        {"MQTT_BROKER_PORT": "0"},
        {"MQTT_BROKER_PORT": "70000"},
        {"MQTT_QOS": "3"},
        {"MQTT_QOS": "-1"},
        {"MQTT_KEEPALIVE": "0"},
        {"MQTT_TOPIC": "   "},
        {"DB_POOL_MIN_SIZE": "0"},
        {"DB_POOL_MIN_SIZE": "12", "DB_POOL_MAX_SIZE": "5"},
        {"DB_COMMAND_TIMEOUT": "0"},
        {"MQTT_RECONNECT_INITIAL_DELAY": "0"},
        {"MQTT_RECONNECT_INITIAL_DELAY": "10", "MQTT_RECONNECT_MAX_DELAY": "5"},
        {"DATABASE_URL": "   "},
    ],
)
def test_config_rejects_invalid_values(env_override: dict[str, str]):
    with pytest.raises(ValueError):
        IngestorConfig.from_env(env_override)
