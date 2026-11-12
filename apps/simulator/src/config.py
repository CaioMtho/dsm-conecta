import argparse
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SimulatorConfig:
    broker_host: str
    broker_port: int
    username: str | None
    password: str | None
    topic_telemetry: str
    topic_status: str
    interval_seconds: float
    people_per_minute: float
    client_id: str


def load_config(args: list[str] | None = None) -> SimulatorConfig:
    parser = argparse.ArgumentParser(description="Simulador de Contagem de Visitantes MQTT")

    parser.add_argument(
        "--host",
        default=os.getenv("MQTT_HOST", "localhost"),
        help="Host do broker MQTT (env: MQTT_HOST)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MQTT_PORT", "1883")),
        help="Porta do broker MQTT (env: MQTT_PORT)",
    )
    parser.add_argument(
        "--username",
        default=os.getenv("MQTT_USERNAME"),
        help="Usuário MQTT (env: MQTT_USERNAME)",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("MQTT_PASSWORD"),
        help="Senha MQTT (env: MQTT_PASSWORD)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=float(os.getenv("SIMULATOR_INTERVAL_SECONDS", "5.0")),
        help="Intervalo de disparo em segundos (env: SIMULATOR_INTERVAL_SECONDS)",
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=float(os.getenv("SIMULATOR_PEOPLE_PER_MINUTE", "12.0")),
        help="Taxa média de pessoas por minuto (env: SIMULATOR_PEOPLE_PER_MINUTE)",
    )
    parser.add_argument(
        "--client-id",
        default=os.getenv("MQTT_CLIENT_ID", "totem-sensor-simulator-01"),
        help="Client ID MQTT (env: MQTT_CLIENT_ID)",
    )

    parsed = parser.parse_args(args)

    return SimulatorConfig(
        broker_host=parsed.host,
        broker_port=parsed.port,
        username=parsed.username,
        password=parsed.password,
        topic_telemetry="dsm/prod/totem/sensor/contagem",
        topic_status="dsm/prod/totem/sensor/status",
        interval_seconds=parsed.interval,
        people_per_minute=parsed.rate,
        client_id=parsed.client_id,
    )
