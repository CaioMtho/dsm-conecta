import argparse
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SimulatorConfig:
    host: str
    port: int
    username: str | None
    password: str | None
    topic_telemetry: str
    topic_status: str
    interval_seconds: float
    rate_per_minute: float
    client_id: str


def load_config(argv: list[str] | None = None) -> SimulatorConfig:
    parser = argparse.ArgumentParser(description="Simulador de sensor MQTT de visitantes")
    parser.add_argument("--host", default=os.getenv("MQTT_HOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MQTT_PORT", "1883")))
    parser.add_argument(
        "--username",
        default=os.getenv("MQTT_USERNAME") or os.getenv("MQTT_SIMULATOR_USER"),
        help="Usuário MQTT (env: MQTT_USERNAME ou MQTT_SIMULATOR_USER)",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("MQTT_PASSWORD") or os.getenv("MQTT_SIMULATOR_PASSWORD"),
        help="Senha MQTT (env: MQTT_PASSWORD ou MQTT_SIMULATOR_PASSWORD)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=float(os.getenv("SIMULATOR_INTERVAL", "5.0")),
        help="Intervalo de publicação em segundos (> 0)",
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=float(os.getenv("SIMULATOR_RATE", "10.0")),
        help="Taxa média de visitantes por minuto (>= 0)",
    )
    parser.add_argument(
        "--client-id",
        default=os.getenv("MQTT_CLIENT_ID", "totem-sensor-simulator-01"),
        help="Client ID MQTT (env: MQTT_CLIENT_ID)",
    )

    args = parser.parse_args(argv)

    if not (1 <= args.port <= 65535):
        raise ValueError(f"Porta MQTT inválida ({args.port}). Deve estar entre 1 e 65535.")
    if args.interval <= 0:
        raise ValueError(f"Intervalo inválido ({args.interval}). Deve ser maior que 0.")
    if args.rate < 0:
        raise ValueError(f"Taxa inválida ({args.rate}). Deve ser maior ou igual a 0.")

    return SimulatorConfig(
        host=args.host,
        port=args.port,
        username=args.username,
        password=args.password,
        topic_telemetry="dsm/prod/totem/sensor/contagem",
        topic_status="dsm/prod/totem/sensor/status",
        interval_seconds=args.interval,
        rate_per_minute=args.rate,
        client_id=args.client_id,
    )
