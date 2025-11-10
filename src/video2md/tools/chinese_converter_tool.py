"""Console script for Chinese converter.

Wrapper to call main() from the existing chinese_converter module.
"""
from __future__ import annotations
from video2md.utils.chinese_converter import main as _cli_main  # type: ignore

import sys
from pathlib import Path

# Ensure src/ is on path for source runs (without install)
_ROOT = Path(__file__).resolve().parents[3]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Use the packaged utils module


def main() -> int:
    _cli_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
