import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

ingestor_dir = str(Path(__file__).resolve().parent.parent)
if ingestor_dir not in sys.path:
    sys.path.insert(0, ingestor_dir)


def test_setup_signal_handlers():
    from ingestor.main import setup_signal_handlers

    loop = asyncio.new_event_loop()
    try:
        stop_event = asyncio.Event()
        with patch.object(loop, "add_signal_handler") as mock_add:
            setup_signal_handlers(loop, stop_event)
            assert mock_add.call_count >= 2
    finally:
        loop.close()


def test_main_entrypoint_runs_and_stops_cleanly():
    from src.main import main

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
