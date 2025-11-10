"""Console script for video to audio converter.

Provides a minimal CLI to convert a video to audio using VideoConverter.
"""
from __future__ import annotations
from video2md.utils.video_converter import VideoConverter  # type: ignore

import argparse
from pathlib import Path
import sys

# Ensure src/ is on path for source runs (without install)
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[3]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Use the packaged utils module


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert a video to audio using FFmpeg (wrapper for VideoConverter)"
    )
    parser.add_argument("input", help="Path to the input video file")
    parser.add_argument("--format", default="wav",
                        help="Audio format (wav, mp3, flac, aac)")
    parser.add_argument("--out", dest="output", default=None,
                        help="Output audio file path")
    parser.add_argument("--out-dir", dest="output_dir",
                        default=None, help="Output directory")
    parser.add_argument("--rate", dest="sample_rate",
                        type=int, default=16000, help="Sample rate")
    parser.add_argument("--channels", type=int, default=1,
                        help="Channels (1 or 2)")
    parser.add_argument("--no-overwrite", dest="overwrite",
                        action="store_false", help="Do not overwrite")

    args = parser.parse_args()

    conv = VideoConverter()
    try:
        result = conv.video_to_audio(
            input_path=Path(args.input),
            output_path=Path(args.output) if args.output else None,
            output_dir=Path(args.output_dir) if args.output_dir else None,
            audio_format=args.format,
            sample_rate=args.sample_rate,
            channels=args.channels,
            overwrite=args.overwrite,
        )
        print(result)
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
