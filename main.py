"""Entry point for the MACS platform."""

import sys
from pydantic import ValidationError
from macs.application.factory import ApplicationFactory
from macs.infrastructure.config import SystemSettings


def main() -> None:
    """Initializes the MACS Application via the Factory Pattern."""
    try:
        # SystemSettings will look for .env or shell environment variables
        settings = SystemSettings()
    except ValidationError as e:
        print(f"Configuration Error: Missing required environment variables.\n{e}")
        sys.exit(1)

    # Placeholder for Queue implementation to be filled in Milestone 2
    queue = None

    orchestrator = ApplicationFactory.create_orchestrator(settings, queue)  # type: ignore
    print(f"MACS Orchestrator initialized successfully with: {orchestrator}")


if __name__ == "__main__":
    main()
