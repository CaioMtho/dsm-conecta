from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

SUPPORTED_SCHEMA_VERSION = "1.0"


class EventSource(str, Enum):
    APP_MOBILE = "app_mobile"
    APP_WEB = "app_web"
    APP_DESKTOP = "app_desktop"
    SENSOR_SIMULATOR = "sensor_simulator"


class EventCategory(str, Enum):
    INTERACAO_TELA = "interacao_tela"
    LEITURA_SENSOR = "leitura_sensor"
    QUESTIONARIO_VOCACIONAL = "questionario_vocacional"
    PRESENCA_EVENTO = "presenca_evento"
    CONTAGEM_ESTANDE = "contagem_estande"


class TelemetryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = Field(
        default=SUPPORTED_SCHEMA_VERSION,
        description="Versão do esquema de mensagens",
    )
    timestamp: datetime = Field(
        description="Momento de ocorrência do evento em UTC",
    )
    event_id: str = Field(
        min_length=1,
        description="Identificador único UUID do evento",
    )
    session_id: str = Field(
        min_length=1,
        description="Identificador UUID anônimo da sessão",
    )
    source: EventSource = Field(
        description="Origem emissora da mensagem",
    )
    category: EventCategory = Field(
        description="Categoria funcional do evento",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Dados específicos contextuais do evento",
    )

    @field_validator("event_id", "session_id", mode="before")
    @classmethod
    def validate_uuid_identifier(cls, value: Any) -> str:
        # Mantém str canônica para compatibilidade com JSON/logs e coluna UUID no TimescaleDB.
        if isinstance(value, UUID):
            return str(value)
        if not isinstance(value, str) or not value.strip():
            raise ValueError("O identificador deve ser um UUID válido.")
        cleaned = value.strip()
        try:
            return str(UUID(cleaned))
        except ValueError as exc:
            raise ValueError(f"O identificador deve ser um UUID válido: {cleaned!r}") from exc

    @field_validator("timestamp")
    @classmethod
    def ensure_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("O timestamp deve incluir fuso horário explícito (UTC).")
        return value.astimezone(UTC)
