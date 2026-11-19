import logging
import signal
import sys
import threading
import uuid

from simulator.client import MqttSensorClient
from simulator.config import load_config
from simulator.generator import create_visitor_event

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    config = load_config(argv)
    stop_event = threading.Event()

    def _handle_signal(signum, frame) -> None:
        logger.info("Sinal %s recebido. Encerrando simulador...", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    client = MqttSensorClient(config, stop_event=stop_event)
    session_id = str(uuid.uuid4())

    try:
        if not client.connect():
            return 1

        while not stop_event.is_set():
            event = create_visitor_event(
                config.rate_per_minute,
                config.interval_seconds,
                session_id,
            )
            client.publish_event(event)
            stop_event.wait(timeout=config.interval_seconds)
    finally:
        client.disconnect()

    return 0


if __name__ == "__main__":
    sys.exit(main())
