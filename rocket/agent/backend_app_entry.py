"""Frozen executable entrypoint for the Rocket Backend desktop app."""

from __future__ import annotations

import sys

from agent.main import app


def main() -> None:
    app(args=sys.argv[1:], standalone_mode=True)


if __name__ == "__main__":
    main()
