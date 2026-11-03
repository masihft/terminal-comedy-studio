"""Allows `python -m terminal_comedian` while the console script is being installed."""

from __future__ import annotations

from .main import main

if __name__ == "__main__":
    raise SystemExit(main())
