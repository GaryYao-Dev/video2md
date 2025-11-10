from pathlib import Path
from typing import Optional
import re


def read_srt_text(srt_path: Path) -> str:
    try:
        return srt_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"[Error reading SRT {srt_path}: {e}]"


def _clean_srt_to_plain(text: str) -> str:
    """Convert SRT content to plain transcript by removing indices and timestamps.

    - Drop lines that are only digits (block indices)
    - Drop lines that contain SRT timecodes (e.g., "00:00:01,000 --> 00:00:05,000")
    - Collapse multiple blank lines
    """
    lines = text.splitlines()
    out_lines = []
    timecode_re = re.compile(
        r"\d{2}:\d{2}:\d{2},\d{3}\s+-->\s+\d{2}:\d{2}:\d{2},\d{3}")
    for line in lines:
        if not line:
            # keep as separator (later dedup)
            out_lines.append("")
            continue
        if line.isdigit():
            continue
        if timecode_re.search(line):
            continue
        out_lines.append(line)
    # Deduplicate excessive blank lines
    cleaned = []
    last_blank = False
    for l in out_lines:
        if l.strip() == "":
            if not last_blank:
                cleaned.append("")
            last_blank = True
        else:
            cleaned.append(l)
            last_blank = False
    return "\n".join(cleaned).strip()


def read_transcript_text(transcript_or_srt_path: Path) -> str:
    """Read a transcript, preferring TXT if available; if SRT, return cleaned plain text.

    If given a .srt path, prefer a sibling .txt if it exists. If only SRT exists,
    strip timecodes and indices to reduce tokens.
    """
    p = Path(transcript_or_srt_path)
    try:
        if p.suffix.lower() == ".srt":
            txt = p.with_suffix(".txt")
            if txt.exists():
                return txt.read_text(encoding="utf-8")
            # fallback: clean srt
            return _clean_srt_to_plain(p.read_text(encoding="utf-8"))
        if p.suffix.lower() == ".txt":
            return p.read_text(encoding="utf-8")
        # Unknown extension: try to read; if it looks like SRT, clean
        data = p.read_text(encoding="utf-8")
        if "-->" in data:
            return _clean_srt_to_plain(data)
        return data
    except Exception as e:
        return f"[Error reading transcript {p}: {e}]"


def find_moved_media(base_name: str, media_dir: Path) -> Optional[Path]:
    if not media_dir.exists():
        return None
    exts = {
        ".mp4",
        ".avi",
        ".mkv",
        ".mov",
        ".wmv",
        ".flv",
        ".webm",
        ".mp3",
        ".wav",
        ".flac",
        ".aac",
        ".ogg",
        ".m4a",
        ".wma",
    }
    candidates = [
        p
        for p in media_dir.iterdir()
        if p.is_file()
        and p.suffix.lower() in exts
        and (p.stem == base_name or p.stem.startswith(base_name + "_"))
    ]
    if not candidates:
        return None
    exact = [p for p in candidates if p.stem == base_name]
    if exact:
        return exact[0]
    return max(candidates, key=lambda p: p.stat().st_mtime)
