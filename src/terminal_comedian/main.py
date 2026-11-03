"""Entry point for the `comedian` console script."""

from __future__ import annotations

import sys

from .cli import main as _main


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except KeyboardInterrupt:
        print()
        return 130


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(sys.exit(main()))
