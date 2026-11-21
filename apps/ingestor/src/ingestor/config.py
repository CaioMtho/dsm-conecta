import math
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import quote_plus

DEFAULT_MQTT_TOPIC = "dsm/prod/#"


def _parse_optional_bool(raw: str | None) -> bool | None:
    if raw is None or not raw.strip():
        return None
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    raise ValueError(f"Valor booleano inválido: {raw!r}.")


@dataclass(frozen=True)
class IngestorConfig:
    database_url: str = field(repr=False)
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: str | None = "ingestor_user"
    mqtt_password: str | None = field(default="ingestor_pass_dev", repr=False)
    mqtt_topic: str = DEFAULT_MQTT_TOPIC
    mqtt_qos: int = 1
    mqtt_keepalive: int = 60
    mqtt_client_id: str | None = None
    mqtt_clean_session: bool | None = None
    mqtt_max_queued_messages: int = 1000
    max_payload_bytes: int = 65536
    max_log_payload_chars: int = 4096
    db_pool_min_size: int = 1
    db_pool_max_size: int = 5
    db_command_timeout: float = 10.0
    db_close_timeout: float = 5.0
    reconnect_initial_delay: float = 1.0
    reconnect_max_delay: float = 30.0
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        if not self.database_url.strip():
            raise ValueError("DATABASE_URL não pode ser vazio.")
        if not self.mqtt_host.strip():
            raise ValueError("MQTT_BROKER_HOST não pode ser vazio.")
        if not (1 <= self.mqtt_port <= 65535):
            raise ValueError(f"Porta MQTT inválida: {self.mqtt_port}.")
        if self.mqtt_qos not in (0, 1, 2):
            raise ValueError(f"QoS MQTT inválido: {self.mqtt_qos}.")
        if self.mqtt_keepalive <= 0:
            raise ValueError(f"Keepalive MQTT inválido: {self.mqtt_keepalive}.")
        if not self.mqtt_topic.strip():
            raise ValueError("MQTT_TOPIC não pode ser vazio.")
        if self.mqtt_clean_session is False and not (
            self.mqtt_client_id and self.mqtt_client_id.strip()
        ):
            raise ValueError(
                "MQTT_CLIENT_ID é obrigatório quando MQTT_CLEAN_SESSION=false."
            )
        if self.mqtt_max_queued_messages < 1:
            raise ValueError(
                f"MQTT_MAX_QUEUED_MESSAGES inválido: {self.mqtt_max_queued_messages}."
            )
        if self.max_payload_bytes < 1:
            raise ValueError(
                f"INGESTOR_MAX_PAYLOAD_BYTES inválido: {self.max_payload_bytes}."
            )
        if self.max_log_payload_chars < 1:
            raise ValueError(
                f"INGESTOR_MAX_LOG_PAYLOAD_CHARS inválido: {self.max_log_payload_chars}."
            )
        if self.db_pool_min_size < 1:
            raise ValueError(f"DB_POOL_MIN_SIZE inválido: {self.db_pool_min_size}.")
        if self.db_pool_max_size < self.db_pool_min_size:
            raise ValueError(
                "DB_POOL_MAX_SIZE deve ser maior ou igual a DB_POOL_MIN_SIZE."
            )
        if not math.isfinite(self.db_command_timeout) or self.db_command_timeout <= 0:
            raise ValueError(f"DB_COMMAND_TIMEOUT inválido: {self.db_command_timeout}.")
        if not math.isfinite(self.db_close_timeout) or self.db_close_timeout <= 0:
            raise ValueError(f"DB_CLOSE_TIMEOUT inválido: {self.db_close_timeout}.")
        if (
            not math.isfinite(self.reconnect_initial_delay)
            or self.reconnect_initial_delay <= 0
        ):
            raise ValueError(
                f"MQTT_RECONNECT_INITIAL_DELAY inválido: {self.reconnect_initial_delay}."
            )
        if (
            not math.isfinite(self.reconnect_max_delay)
            or self.reconnect_max_delay < self.reconnect_initial_delay
        ):
            raise ValueError(
                "MQTT_RECONNECT_MAX_DELAY deve ser finito e >= MQTT_RECONNECT_INITIAL_DELAY."
            )

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "IngestorConfig":
        source = os.environ if env is None else env

        if "DATABASE_URL" in source:
            database_url = source["DATABASE_URL"]
        else:
            pg_user = quote_plus(source.get("POSTGRES_USER", "dsm_user"))
            pg_password = quote_plus(source.get("POSTGRES_PASSWORD", "dsm_password"))
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
            mqtt_clean_session=_parse_optional_bool(source.get("MQTT_CLEAN_SESSION")),
            mqtt_max_queued_messages=int(source.get("MQTT_MAX_QUEUED_MESSAGES", "1000")),
            max_payload_bytes=int(source.get("INGESTOR_MAX_PAYLOAD_BYTES", "65536")),
            max_log_payload_chars=int(source.get("INGESTOR_MAX_LOG_PAYLOAD_CHARS", "4096")),
            db_pool_min_size=int(source.get("DB_POOL_MIN_SIZE", "1")),
            db_pool_max_size=int(source.get("DB_POOL_MAX_SIZE", "5")),
            db_command_timeout=float(source.get("DB_COMMAND_TIMEOUT", "10.0")),
            db_close_timeout=float(source.get("DB_CLOSE_TIMEOUT", "5.0")),
            reconnect_initial_delay=float(source.get("MQTT_RECONNECT_INITIAL_DELAY", "1.0")),
            reconnect_max_delay=float(source.get("MQTT_RECONNECT_MAX_DELAY", "30.0")),
            log_level=source.get("LOG_LEVEL", "INFO").upper(),
        )
