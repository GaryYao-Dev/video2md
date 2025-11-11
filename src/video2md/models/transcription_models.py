"""
Transcription data models
Based on BiliNote's transcriber models with adaptations for video2md
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TranscriptSegment:
    """Single transcription segment with timestamp"""
    start: float      # Start time in seconds
    end: float        # End time in seconds
    text: str         # Transcribed text for this segment


@dataclass
class TranscriptResult:
    """Complete transcription result"""
    language: Optional[str]                # Detected language (e.g., "zh", "en")
    full_text: str                         # Complete merged text
    segments: List[TranscriptSegment]      # Segmented structure for subtitles
    raw: Optional[dict] = None             # Raw response data for debugging
