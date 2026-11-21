import asyncio
import io
import json
import logging
import signal
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

from ingestor.logging_config import JsonLogFormatter

ingestor_dir = str(Path(__file__).resolve().parent.parent)
if ingestor_dir not in sys.path:
    sys.path.insert(0, ingestor_dir)


def test_setup_signal_handlers_triggers_stop_and_logs_json():
    from ingestor.main import setup_signal_handlers

    stream = io.StringIO()
    logger = logging.getLogger("test.ingestor.signals")
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonLogFormatter())
    logger.addHandler(handler)

    registered: dict[signal.Signals, tuple] = {}
    loop = asyncio.new_event_loop()
    try:
        stop_event = asyncio.Event()

        def _fake_add_signal_handler(sig, callback, *args):
            registered[sig] = (callback, args)

        with patch.object(loop, "add_signal_handler", side_effect=_fake_add_signal_handler):
            setup_signal_handlers(loop, stop_event, logger=logger)

        assert signal.SIGINT in registered
        assert signal.SIGTERM in registered

        callback, args = registered[signal.SIGTERM]
        callback(*args)

        assert stop_event.is_set() is True
        log_entry = json.loads(stream.getvalue().strip())
        assert log_entry["event"] == "shutdown_signal_received"
        assert log_entry["signal"] == "SIGTERM"
    finally:
        loop.close()


def test_main_entrypoint_runs_and_stops_cleanly(monkeypatch):
    from src.main import main

    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    monkeypatch.setenv("MQTT_BROKER_HOST", "localhost")
    monkeypatch.setenv("MQTT_BROKER_PORT", "1883")

    stop_event = asyncio.Event()
    stop_event.set()

    with patch("ingestor.main.TelemetryRepository") as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.connect = AsyncMock()
        mock_repo.close = AsyncMock()

        exit_code = main(stop_event=stop_event)

    assert exit_code == 0
    mock_repo.connect.assert_awaited_once()
    mock_repo.close.assert_awaited_once()
