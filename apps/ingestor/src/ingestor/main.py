import asyncio
import logging
import signal
import sys

from ingestor.config import IngestorConfig
from ingestor.logging_config import configure_logging, log_structured
from ingestor.repository import TelemetryRepository
from ingestor.service import IngestorService


def setup_signal_handlers(
    loop: asyncio.AbstractEventLoop,
    stop_event: asyncio.Event,
    logger: logging.Logger | None = None,
) -> None:
    target_logger = logger or logging.getLogger("ingestor")

    def _on_signal(sig: signal.Signals) -> None:
        log_structured(
            target_logger,
            logging.INFO,
            "shutdown_signal_received",
            signal=sig.name,
        )
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _on_signal, sig)
        except (NotImplementedError, ValueError, RuntimeError):
            pass


async def run_service(
    config: IngestorConfig | None = None,
    stop_event: asyncio.Event | None = None,
) -> int:
    resolved_config = config or IngestorConfig.from_env()
    logger = configure_logging(level=resolved_config.log_level)
    target_stop = stop_event or asyncio.Event()

    if stop_event is None:
        setup_signal_handlers(asyncio.get_running_loop(), target_stop, logger=logger)

    repository = TelemetryRepository(
        dsn=resolved_config.database_url,
        min_size=resolved_config.db_pool_min_size,
        max_size=resolved_config.db_pool_max_size,
        command_timeout=resolved_config.db_command_timeout,
    )
    service = IngestorService(
        config=resolved_config,
        repository=repository,
        logger=logger,
    )
    await service.run(stop_event=target_stop)
    return 0


def main(stop_event: asyncio.Event | None = None) -> int:
    return asyncio.run(run_service(stop_event=stop_event))


if __name__ == "__main__":
    sys.exit(main())
