from datetime import datetime
from enum import Enum
from typing import Any, Literal

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
        description="Identificador único e aleatório do evento",
    )
    session_id: str = Field(
        min_length=1,
        description="Identificador aleatório e anônimo da sessão",
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

    @field_validator("event_id", "session_id")
    @classmethod
    def check_non_empty_string(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("O identificador não pode ser vazio ou conter apenas espaços.")
        return v.strip()
