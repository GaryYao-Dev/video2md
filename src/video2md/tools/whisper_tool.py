"""Console script for whisper client.

This wrapper calls the main() from the existing whisper_client module.
It injects the repo root to sys.path for source runs.
"""
from __future__ import annotations
from video2md.clients.whisper_client import main as _cli_main  # type: ignore

import sys
from pathlib import Path

# Ensure src/ is on path for source runs (without install)
_ROOT = Path(__file__).resolve().parents[3]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


# Use the packaged client module

def main() -> int:
    return _cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
