import logging
import signal
import sys
import time
import uuid

from src.client import MqttSensorClient
from src.config import load_config
from src.generator import create_visitor_event

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("simulator")


def main() -> None:
    config = load_config()
    session_id = f"sim-session-{uuid.uuid4()}"
    sensor = MqttSensorClient(config)
    running = True

    def handle_shutdown(signum: int, frame: object) -> None:
        nonlocal running
        logger.info("Encerrando simulador...")
        running = False

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    sensor.connect()

    try:
        while running:
            event = create_visitor_event(
                people_per_minute=config.people_per_minute,
                interval_seconds=config.interval_seconds,
                session_id=session_id,
            )
            if sensor.publish_event(event):
                logger.info(
                    "Evento publicado | id=%s | visitantes=%s",
                    event.event_id,
                    event.payload["visitor_count"],
                )
            time.sleep(config.interval_seconds)
    finally:
        sensor.disconnect()
        sys.exit(0)


if __name__ == "__main__":
    main()
