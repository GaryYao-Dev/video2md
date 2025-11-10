from video2md.clients.whisper_client import transcribe_media as whisper_transcribe
import asyncio
from mcp.server.fastmcp import FastMCP
from typing import Optional

mcp = FastMCP("whisper_server")


@mcp.tool()
async def transcribe_media(media_file_path: str, output_dir: Optional[str] = None) -> str:
    """Transcribe media using Whisper.

    Parameters
    ----------
    media_file_path : str
      Absolute or relative path to the media file.
    output_dir : Optional[str]
      Directory to write transcript artifacts (.srt/.txt). If omitted, falls back
      to the whisper client default ("whisper_output").

    Returns
    -------
    str
      Raw transcription text (may be SRT content if output_format is srt).
    """
    kwargs = {}
    if output_dir:
        kwargs["output_dir"] = output_dir
    # Run blocking I/O in a thread so we don't block the event loop
    result = await asyncio.to_thread(whisper_transcribe, media_file_path, **kwargs)
    return result


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
