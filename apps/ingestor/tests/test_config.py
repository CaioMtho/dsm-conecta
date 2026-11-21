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
    assert cfg.mqtt_client_id is None
    assert cfg.mqtt_clean_session is None
    assert cfg.mqtt_max_queued_messages == 1000
    assert cfg.max_payload_bytes == 65536
    assert cfg.max_log_payload_chars == 4096
    assert cfg.database_url == "postgresql://dsm_user:dsm_password@localhost:5432/dsm_conecta"
    assert cfg.db_pool_min_size == 1
    assert cfg.db_pool_max_size == 5
    assert cfg.db_command_timeout == 10.0
    assert cfg.db_close_timeout == 5.0
    assert cfg.reconnect_initial_delay == 1.0
    assert cfg.reconnect_max_delay == 30.0
    assert cfg.log_level == "INFO"


def test_config_repr_hides_credentials():
    cfg = IngestorConfig.from_env(
        {
            "DATABASE_URL": "postgresql://prod_user:super_secret_db@db:5432/prod_db",
            "MQTT_BROKER_PASSWORD": "super_secret_mqtt",
        }
    )

    rendered = repr(cfg)
    assert "super_secret_db" not in rendered
    assert "super_secret_mqtt" not in rendered


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
        "MQTT_CLEAN_SESSION": "false",
        "MQTT_MAX_QUEUED_MESSAGES": "250",
        "INGESTOR_MAX_PAYLOAD_BYTES": "32768",
        "INGESTOR_MAX_LOG_PAYLOAD_CHARS": "2048",
        "DB_POOL_MIN_SIZE": "3",
        "DB_POOL_MAX_SIZE": "15",
        "DB_COMMAND_TIMEOUT": "15.5",
        "DB_CLOSE_TIMEOUT": "7.5",
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
    assert cfg.mqtt_clean_session is False
    assert cfg.mqtt_max_queued_messages == 250
    assert cfg.max_payload_bytes == 32768
    assert cfg.max_log_payload_chars == 2048
    assert cfg.db_pool_min_size == 3
    assert cfg.db_pool_max_size == 15
    assert cfg.db_command_timeout == 15.5
    assert cfg.db_close_timeout == 7.5
    assert cfg.reconnect_initial_delay == 0.5
    assert cfg.reconnect_max_delay == 20.0
    assert cfg.log_level == "DEBUG"


def test_config_fallback_encodes_special_characters_in_dsn():
    env = {
        "POSTGRES_USER": "user@org",
        "POSTGRES_PASSWORD": "p@ss:w/rd#1",
        "POSTGRES_HOST": "timescale.local",
        "POSTGRES_PORT": "5433",
        "POSTGRES_DB": "telemetry_db",
        "MQTT_INGESTOR_USER": "ingestor_alt",
        "MQTT_INGESTOR_PASSWORD": "ingestor_alt_pw",
    }

    cfg = IngestorConfig.from_env(env)

    assert (
        cfg.database_url
        == "postgresql://user%40org:p%40ss%3Aw%2Frd%231@timescale.local:5433/telemetry_db"
    )
    assert cfg.mqtt_username == "ingestor_alt"
    assert cfg.mqtt_password == "ingestor_alt_pw"


@pytest.mark.parametrize(
    "env_override",
    [
        {"MQTT_BROKER_HOST": "   "},
        {"MQTT_BROKER_PORT": "0"},
        {"MQTT_BROKER_PORT": "70000"},
        {"MQTT_QOS": "3"},
        {"MQTT_QOS": "-1"},
        {"MQTT_KEEPALIVE": "0"},
        {"MQTT_TOPIC": "   "},
        {"MQTT_CLEAN_SESSION": "false"},
        {"MQTT_CLEAN_SESSION": "maybe"},
        {"MQTT_MAX_QUEUED_MESSAGES": "0"},
        {"INGESTOR_MAX_PAYLOAD_BYTES": "0"},
        {"INGESTOR_MAX_LOG_PAYLOAD_CHARS": "0"},
        {"DB_POOL_MIN_SIZE": "0"},
        {"DB_POOL_MIN_SIZE": "12", "DB_POOL_MAX_SIZE": "5"},
        {"DB_COMMAND_TIMEOUT": "0"},
        {"DB_COMMAND_TIMEOUT": "nan"},
        {"DB_CLOSE_TIMEOUT": "inf"},
        {"MQTT_RECONNECT_INITIAL_DELAY": "0"},
        {"MQTT_RECONNECT_INITIAL_DELAY": "nan"},
        {"MQTT_RECONNECT_INITIAL_DELAY": "10", "MQTT_RECONNECT_MAX_DELAY": "5"},
        {"MQTT_RECONNECT_MAX_DELAY": "inf"},
        {"DATABASE_URL": "   "},
    ],
)
def test_config_rejects_invalid_values(env_override: dict[str, str]):
    with pytest.raises(ValueError):
        IngestorConfig.from_env(env_override)
