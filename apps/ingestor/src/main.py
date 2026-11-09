import logging
import signal
import sys
import threading

logger = logging.getLogger("ingestor")


class IngestorService:
    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def run(self, stop_event: threading.Event | None = None) -> None:
        target_event = stop_event or self._stop_event
        self._is_running = True
        logger.info("Ingestor service running and waiting for events...")
        try:
            while not target_event.is_set():
                target_event.wait(timeout=0.5)
        finally:
            self._is_running = False
            logger.info("Ingestor service stopped.")

    def stop(self) -> None:
        self._stop_event.set()


def setup_signal_handlers(stop_event: threading.Event) -> None:
    def _signal_handler(signum, frame):
        logger.info("Received termination signal %s. Shutting down...", signum)
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _signal_handler)
        except (ValueError, AttributeError):
            pass


def main(stop_event: threading.Event | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    if stop_event is None:
        stop_event = threading.Event()
        setup_signal_handlers(stop_event)

    service = IngestorService()
    service.run(stop_event=stop_event)
    return 0


if __name__ == "__main__":
    sys.exit(main())
