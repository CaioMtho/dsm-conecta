import sys

from ingestor.main import main, run_service, setup_signal_handlers
from ingestor.service import IngestorService

__all__ = [
    "IngestorService",
    "main",
    "run_service",
    "setup_signal_handlers",
]

if __name__ == "__main__":
    sys.exit(main())
