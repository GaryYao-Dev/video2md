"""
Transcription format conversion utilities
Convert TranscriptResult to various formats (SRT, TXT, VTT, JSON)
"""
import json
import logging
from datetime import timedelta
from pathlib import Path
from typing import Union
from dataclasses import asdict

from video2md.models.transcription_models import TranscriptResult, TranscriptSegment

logger = logging.getLogger(__name__)


def format_timestamp_srt(seconds: float) -> str:
    """
    Format seconds to SRT timestamp format (HH:MM:SS,mmm)
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted timestamp string
    """
    td = timedelta(seconds=seconds)
    hours = int(td.total_seconds() // 3600)
    minutes = int((td.total_seconds() % 3600) // 60)
    secs = int(td.total_seconds() % 60)
    millis = int((td.total_seconds() % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def format_timestamp_vtt(seconds: float) -> str:
    """
    Format seconds to VTT timestamp format (HH:MM:SS.mmm)
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted timestamp string
    """
    td = timedelta(seconds=seconds)
    hours = int(td.total_seconds() // 3600)
    minutes = int((td.total_seconds() % 3600) // 60)
    secs = int(td.total_seconds() % 60)
    millis = int((td.total_seconds() % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def transcript_to_srt(transcript: TranscriptResult) -> str:
    """
    Convert TranscriptResult to SRT subtitle format
    
    Args:
        transcript: Transcript result with segments
        
    Returns:
        SRT formatted string
    """
    srt_content = []
    
    for i, segment in enumerate(transcript.segments, start=1):
        # Subtitle number
        srt_content.append(str(i))
        
        # Timestamp line
        start_time = format_timestamp_srt(segment.start)
        end_time = format_timestamp_srt(segment.end)
        srt_content.append(f"{start_time} --> {end_time}")
        
        # Subtitle text
        srt_content.append(segment.text)
        
        # Empty line separator
        srt_content.append("")
    
    return "\n".join(srt_content)


def transcript_to_vtt(transcript: TranscriptResult) -> str:
    """
    Convert TranscriptResult to WebVTT subtitle format
    
    Args:
        transcript: Transcript result with segments
        
    Returns:
        VTT formatted string
    """
    vtt_content = ["WEBVTT", ""]
    
    for segment in transcript.segments:
        start_time = format_timestamp_vtt(segment.start)
        end_time = format_timestamp_vtt(segment.end)
        vtt_content.append(f"{start_time} --> {end_time}")
        vtt_content.append(segment.text)
        vtt_content.append("")
    
    return "\n".join(vtt_content)


def transcript_to_txt(
    transcript: TranscriptResult,
    include_timestamps: bool = False,
    include_metadata: bool = False
) -> str:
    """
    Convert TranscriptResult to plain text format
    
    Args:
        transcript: Transcript result with segments
        include_timestamps: Whether to include timestamps for each segment
        include_metadata: Whether to include language and other metadata
        
    Returns:
        Plain text string
    """
    lines = []
    
    # Add metadata if requested
    if include_metadata:
        lines.append(f"Language: {transcript.language or 'Unknown'}")
        lines.append(f"Segments: {len(transcript.segments)}")
        lines.append("-" * 60)
        lines.append("")
    
    if include_timestamps:
        # Include timestamps with text
        for segment in transcript.segments:
            timestamp = f"[{segment.start:.2f}s - {segment.end:.2f}s]"
            lines.append(f"{timestamp} {segment.text}")
    else:
        # Just the full text without timestamps
        for segment in transcript.segments:
          lines.append(segment.text)
    
    return "\n".join(lines)


def transcript_to_json(transcript: TranscriptResult, pretty: bool = True) -> str:
    """
    Convert TranscriptResult to JSON format
    
    Args:
        transcript: Transcript result with segments
        pretty: Whether to format JSON with indentation
        
    Returns:
        JSON formatted string
    """
    data = asdict(transcript)
    
    if pretty:
        return json.dumps(data, ensure_ascii=False, indent=2)
    else:
        return json.dumps(data, ensure_ascii=False)


def save_transcript(
    transcript: TranscriptResult,
    output_path: Union[str, Path],
    format: str = "auto",
    **kwargs
):
    """
    Save transcript to file in specified format
    
    Args:
        transcript: Transcript result to save
        output_path: Output file path
        format: Output format ('auto', 'srt', 'vtt', 'txt', 'json')
                'auto' detects from file extension
        **kwargs: Additional arguments passed to format-specific functions
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Auto-detect format from extension
    if format == "auto":
        ext = output_path.suffix.lower()
        format_map = {
            ".srt": "srt",
            ".vtt": "vtt",
            ".txt": "txt",
            ".json": "json",
        }
        format = format_map.get(ext, "txt")
    
    # Convert to appropriate format
    if format == "srt":
        content = transcript_to_srt(transcript)
    elif format == "vtt":
        content = transcript_to_vtt(transcript)
    elif format == "json":
        content = transcript_to_json(transcript, **kwargs)
    elif format == "txt":
        content = transcript_to_txt(transcript, **kwargs)
    else:
        raise ValueError(f"Unsupported format: {format}")
    
    # Write to file
    output_path.write_text(content, encoding="utf-8")
    
    return str(output_path)


def load_transcript_from_json(json_path: Union[str, Path]) -> TranscriptResult:
    """
    Load TranscriptResult from JSON file
    
    Args:
        json_path: Path to JSON file
        
    Returns:
        TranscriptResult object
    """
    json_path = Path(json_path)
    
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")
    
    data = json.loads(json_path.read_text(encoding="utf-8"))
    
    # Reconstruct segments
    segments = [
        TranscriptSegment(**seg)
        for seg in data.get("segments", [])
    ]
    
    # Reconstruct result
    result = TranscriptResult(
        language=data.get("language"),
        full_text=data.get("full_text", ""),
        segments=segments,
        raw=data.get("raw")
    )
    
    return result


def main():
    """Command-line interface for format conversion"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Convert transcript JSON to various formats"
    )
    parser.add_argument(
        "input_json",
        type=str,
        help="Input JSON file with transcript"
    )
    parser.add_argument(
        "output_file",
        type=str,
        help="Output file path"
    )
    parser.add_argument(
        "--format",
        type=str,
        default="auto",
        choices=["auto", "srt", "vtt", "txt", "json"],
        help="Output format (default: auto-detect from extension)"
    )
    parser.add_argument(
        "--include-timestamps",
        action="store_true",
        help="Include timestamps in TXT format"
    )
    parser.add_argument(
        "--include-metadata",
        action="store_true",
        help="Include metadata in TXT format"
    )
    
    args = parser.parse_args()
    
    try:
        # Load transcript
        print(f"Loading transcript from: {args.input_json}")
        transcript = load_transcript_from_json(args.input_json)
        
        # Save in requested format
        kwargs = {}
        if args.format == "txt":
            kwargs["include_timestamps"] = args.include_timestamps
            kwargs["include_metadata"] = args.include_metadata
        
        output_path = save_transcript(
            transcript,
            args.output_file,
            format=args.format,
            **kwargs
        )
        
        print(f"Transcript saved to: {output_path}")
        print(f"Format: {args.format}")
        print(f"Segments: {len(transcript.segments)}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
