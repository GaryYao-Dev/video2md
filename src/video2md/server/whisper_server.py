from video2md.clients.whisper_client import WhisperClient
from video2md.utils.transcript_converter import save_transcript
import asyncio
from mcp.server.fastmcp import FastMCP
from typing import Optional
from pathlib import Path

mcp = FastMCP("whisper_server")

# Initialize Whisper client as a singleton
_whisper_client = None


def get_whisper_client() -> WhisperClient:
    """Get or create the singleton Whisper client."""
    global _whisper_client
    if _whisper_client is None:
        _whisper_client = WhisperClient()
    return _whisper_client


@mcp.tool()
async def transcribe_media(media_file_path: str, output_dir: Optional[str] = None) -> str:
    """Transcribe media using local Whisper.

    Parameters
    ----------
    media_file_path : str
      Absolute or relative path to the media file.
    output_dir : Optional[str]
      Directory to write transcript artifacts (.srt/.txt). If omitted, falls back
      to the current directory.

    Returns
    -------
    str
      SRT formatted transcription content with timestamps.
    """
    # Run blocking I/O in a thread so we don't block the event loop
    def _transcribe():
        client = get_whisper_client()
        media_path = Path(media_file_path)
        
        # Check if it's a video or audio file
        from video2md.utils.video_converter import VideoConverter
        converter = VideoConverter()
        
        # Transcribe (handles both video and audio)
        if converter.is_video_file(media_path):
            result = client.transcribe_with_video(
                video_file_path=str(media_path),
                language=None,  # Auto-detect
            )
        else:
            result = client.transcribe(
                audio_file_path=str(media_path),
                language=None,  # Auto-detect
            )
        
        # Save to output directory if specified
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Save as SRT and TXT
            base_name = media_path.stem
            save_transcript(result, output_path / f"{base_name}.srt", format="srt")
            save_transcript(result, output_path / f"{base_name}.txt", format="txt")
            save_transcript(result, output_path / f"{base_name}.json", format="json")
        
        # Return SRT content for backward compatibility
        from video2md.utils.transcript_converter import transcript_to_srt
        return transcript_to_srt(result)
    
    result = await asyncio.to_thread(_transcribe)
    return result


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
