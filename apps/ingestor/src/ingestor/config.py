import os
from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_MQTT_TOPIC = "dsm/prod/#"


@dataclass(frozen=True)
class IngestorConfig:
    database_url: str
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: str | None = "ingestor_user"
    mqtt_password: str | None = "ingestor_pass_dev"
    mqtt_topic: str = DEFAULT_MQTT_TOPIC
    mqtt_qos: int = 1
    mqtt_keepalive: int = 60
    mqtt_client_id: str | None = None
    db_pool_min_size: int = 2
    db_pool_max_size: int = 10
    db_command_timeout: float = 10.0
    reconnect_initial_delay: float = 1.0
    reconnect_max_delay: float = 30.0
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        if not self.database_url.strip():
            raise ValueError("DATABASE_URL não pode ser vazio.")
        if not (1 <= self.mqtt_port <= 65535):
            raise ValueError(f"Porta MQTT inválida: {self.mqtt_port}.")
        if self.mqtt_qos not in (0, 1, 2):
            raise ValueError(f"QoS MQTT inválido: {self.mqtt_qos}.")
        if self.mqtt_keepalive <= 0:
            raise ValueError(f"Keepalive MQTT inválido: {self.mqtt_keepalive}.")
        if not self.mqtt_topic.strip():
            raise ValueError("MQTT_TOPIC não pode ser vazio.")
        if self.db_pool_min_size < 1:
            raise ValueError(f"DB_POOL_MIN_SIZE inválido: {self.db_pool_min_size}.")
        if self.db_pool_max_size < self.db_pool_min_size:
            raise ValueError("DB_POOL_MAX_SIZE deve ser maior ou igual a DB_POOL_MIN_SIZE.")
        if self.db_command_timeout <= 0:
            raise ValueError(f"DB_COMMAND_TIMEOUT inválido: {self.db_command_timeout}.")
        if self.reconnect_initial_delay <= 0:
            raise ValueError(
                f"MQTT_RECONNECT_INITIAL_DELAY inválido: {self.reconnect_initial_delay}."
            )
        if self.reconnect_max_delay < self.reconnect_initial_delay:
            raise ValueError(
                "MQTT_RECONNECT_MAX_DELAY deve ser maior ou igual a MQTT_RECONNECT_INITIAL_DELAY."
            )

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "IngestorConfig":
        source = os.environ if env is None else env

        if "DATABASE_URL" in source:
            database_url = source["DATABASE_URL"]
        else:
            pg_user = source.get("POSTGRES_USER", "dsm_user")
            pg_password = source.get("POSTGRES_PASSWORD", "dsm_password")
            pg_host = source.get("POSTGRES_HOST", "localhost")
            pg_port = source.get("POSTGRES_PORT", "5432")
            pg_db = source.get("POSTGRES_DB", "dsm_conecta")
            database_url = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"

        username = source.get("MQTT_BROKER_USER")
        if username is None:
            username = source.get("MQTT_INGESTOR_USER", "ingestor_user")

        password = source.get("MQTT_BROKER_PASSWORD")
        if password is None:
            password = source.get("MQTT_INGESTOR_PASSWORD", "ingestor_pass_dev")

        return cls(
            database_url=database_url,
            mqtt_host=source.get("MQTT_BROKER_HOST", "localhost"),
            mqtt_port=int(source.get("MQTT_BROKER_PORT", "1883")),
            mqtt_username=username,
            mqtt_password=password,
            mqtt_topic=source.get("MQTT_TOPIC", DEFAULT_MQTT_TOPIC),
            mqtt_qos=int(source.get("MQTT_QOS", "1")),
            mqtt_keepalive=int(source.get("MQTT_KEEPALIVE", "60")),
            mqtt_client_id=source.get("MQTT_CLIENT_ID") or None,
            db_pool_min_size=int(source.get("DB_POOL_MIN_SIZE", "2")),
            db_pool_max_size=int(source.get("DB_POOL_MAX_SIZE", "10")),
            db_command_timeout=float(source.get("DB_COMMAND_TIMEOUT", "10.0")),
            reconnect_initial_delay=float(source.get("MQTT_RECONNECT_INITIAL_DELAY", "1.0")),
            reconnect_max_delay=float(source.get("MQTT_RECONNECT_MAX_DELAY", "30.0")),
            log_level=source.get("LOG_LEVEL", "INFO").upper(),
        )
