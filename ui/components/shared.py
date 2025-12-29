"""
Shared utilities and constants for UI components.

This module contains:
- Common path constants (INPUT_DIR, OUTPUT_DIR)
- File extension definitions
- Utility functions for listing files and reading content
"""

from pathlib import Path
from typing import List, Optional
import re

try:
    import gradio as gr  # type: ignore
except Exception:  # pragma: no cover
    gr = None


# ============================================================
# Constants
# ============================================================

INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")

MEDIA_EXTENSIONS = {
    ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm",
    ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma",
}

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"}


# ============================================================
# File Listing Functions
# ============================================================

def list_media_in_input() -> List[str]:
    """List all media files in the input directory."""
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    return [
        str(p.relative_to(INPUT_DIR))
        for p in INPUT_DIR.rglob("*")
        if p.is_file() and p.suffix.lower() in MEDIA_EXTENSIONS
    ]


def list_basenames() -> List[str]:
    """List basenames of processed output folders.
    
    A folder is considered valid if it contains any of:
    <name>.md, <name>.txt, <name>.srt, or <name>.json
    """
    names = set()
    if OUTPUT_DIR.exists():
        for sub in OUTPUT_DIR.iterdir():
            if not sub.is_dir():
                continue
            name = sub.name
            if (sub / f"{name}.md").exists() or \
               (sub / f"{name}.txt").exists() or \
               (sub / f"{name}.srt").exists() or \
               (sub / f"{name}.json").exists():
                names.add(name)
    return sorted(names)


def is_video_file(name: str) -> bool:
    """Check if a file is a video file based on extension."""
    return Path(name).suffix.lower() in VIDEO_EXTENSIONS


# ============================================================
# File Reading Functions
# ============================================================

def read_text_file(path: Path) -> Optional[str]:
    """Safely read a text file, returning None if not found."""
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return None
    return None


def extract_media_path_from_md(md_text: str, base_dir: Path) -> Optional[str]:
    """Extract embedded media path from markdown content.
    
    Looks for video/audio tags or markdown video patterns.
    """
    if not md_text:
        return None
    
    # Look for <video> or <audio> tags
    tag_match = re.search(r'<(video|audio)[^>]*src=["\']([^"\']+)["\']', md_text)
    if tag_match:
        src = tag_match.group(2)
        if src.startswith(("http://", "https://")):
            return src
        media_path = base_dir / src
        if media_path.exists():
            return str(media_path)
    
    # Look for markdown video pattern: ![video](path)
    md_match = re.search(r'!\[video\]\(([^)]+)\)', md_text)
    if md_match:
        src = md_match.group(1)
        media_path = base_dir / src
        if media_path.exists():
            return str(media_path)
    
    return None


def sanitize_md_for_display(md_text: str) -> str:
    """Clean markdown text for display, removing video tags."""
    if not md_text:
        return ""
    # Remove video tags (they'll be shown in the player)
    cleaned = re.sub(
        r"<video[\s\S]*?</video>", "\n> [Video preview is shown in the player above]\n", 
        md_text, flags=re.IGNORECASE
    )
    return cleaned
