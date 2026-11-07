import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch

ingestor_dir = str(Path(__file__).resolve().parent.parent)
if ingestor_dir not in sys.path:
    sys.path.insert(0, ingestor_dir)


def test_ingestor_service_lifecycle():
    from src.main import IngestorService

    service = IngestorService()
    assert not service.is_running

    thread = threading.Thread(target=service.run, daemon=True)
    thread.start()

    time.sleep(0.05)
    assert service.is_running

    service.stop()
    thread.join(timeout=1.0)
    assert not thread.is_alive()
    assert not service.is_running


def test_setup_signal_handlers():
    from src.main import setup_signal_handlers

    stop_event = threading.Event()
    with patch("signal.signal") as mock_signal:
        setup_signal_handlers(stop_event)
        assert mock_signal.call_count >= 2


def test_main_function_runs_and_stops():
    from src.main import main

    stop_event = threading.Event()
    stop_event.set()
    exit_code = main(stop_event=stop_event)
    assert exit_code == 0
