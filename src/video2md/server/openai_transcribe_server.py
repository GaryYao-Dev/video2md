"""
MCP server exposing OpenAI transcription tools.
"""
from __future__ import annotations
from mcp.server import Server
from mcp.types import Tool, TextContent
import json
import logging
from pathlib import Path
import asyncio

from video2md.clients.openai_transcribe_client import OpenAITranscribeClient
from video2md.utils.transcript_converter import save_transcript, transcript_to_srt

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Server("openai-transcribe")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available OpenAI transcription tools."""
    return [
        Tool(
            name="transcribe_audio_openai",
            description=(
                "Transcribe audio file to text using OpenAI's whisper-1 model. "
                "Returns the full transcription text with timestamps. "
                "Supports multiple audio formats (mp3, wav, m4a, etc.). "
                "Language is auto-detected unless specified. "
                "Saves SRT, TXT, and JSON files if output_dir is provided."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the audio file to transcribe"
                    },
                    "language": {
                        "type": "string",
                        "description": "Optional: Language code (e.g., 'zh' for Chinese, 'en' for English). Auto-detect if not specified."
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Optional: Prompt to guide the transcription style or vocabulary"
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Optional: Directory to save transcript files (.srt, .txt, .json). If omitted, files are not saved to disk."
                    },
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="transcribe_video_openai",
            description=(
                "Transcribe video file to text using OpenAI's whisper-1 model. "
                "Extracts audio from video first, then transcribes it. "
                "Returns the full transcription text with timestamps. "
                "Supports multiple video formats (mp4, avi, mkv, etc.). "
                "Language is auto-detected unless specified. "
                "Saves SRT, TXT, and JSON files if output_dir is provided."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the video file to transcribe"
                    },
                    "language": {
                        "type": "string",
                        "description": "Optional: Language code (e.g., 'zh' for Chinese, 'en' for English). Auto-detect if not specified."
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Optional: Prompt to guide the transcription style or vocabulary"
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Optional: Directory to save transcript files (.srt, .txt, .json). If omitted, files are not saved to disk."
                    },
                },
                "required": ["file_path"]
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls for OpenAI transcription."""
    
    if name == "transcribe_audio_openai":
        file_path = arguments.get("file_path")
        language = arguments.get("language")
        prompt = arguments.get("prompt")
        output_dir = arguments.get("output_dir")
        
        if not file_path:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "file_path is required"})
            )]
        
        try:
            # Initialize client
            client = OpenAITranscribeClient()
            
            # Run transcription in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: client.transcribe(
                    audio_file_path=file_path,
                    language=language,
                    prompt=prompt,
                )
            )
            
            # Save to output directory if specified
            if output_dir:
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
                
                base_name = Path(file_path).stem
                
                # Save as SRT, TXT, and JSON (matching local whisper behavior)
                await loop.run_in_executor(
                    None,
                    lambda: save_transcript(result, output_path / f"{base_name}.srt", format="srt")
                )
                await loop.run_in_executor(
                    None,
                    lambda: save_transcript(result, output_path / f"{base_name}.txt", format="txt")
                )
                await loop.run_in_executor(
                    None,
                    lambda: save_transcript(result, output_path / f"{base_name}.json", format="json")
                )
                
                logger.info(f"Saved transcription files to {output_path}")
            
            # Return SRT content for backward compatibility (matching local whisper)
            srt_content = transcript_to_srt(result)
            
            return [TextContent(
                type="text",
                text=srt_content
            )]
            
        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"File not found: {str(e)}"})
            )]
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Transcription failed: {str(e)}"})
            )]
    
    elif name == "transcribe_video_openai":
        file_path = arguments.get("file_path")
        language = arguments.get("language")
        prompt = arguments.get("prompt")
        output_dir = arguments.get("output_dir")
        
        if not file_path:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "file_path is required"})
            )]
        
        try:
            # Initialize client
            client = OpenAITranscribeClient()
            
            # Run transcription in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: client.transcribe_with_video(
                    video_file_path=file_path,
                    language=language,
                    prompt=prompt,
                )
            )
            
            # Save to output directory if specified
            if output_dir:
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
                
                base_name = Path(file_path).stem
                
                # Save as SRT, TXT, and JSON (matching local whisper behavior)
                await loop.run_in_executor(
                    None,
                    lambda: save_transcript(result, output_path / f"{base_name}.srt", format="srt")
                )
                await loop.run_in_executor(
                    None,
                    lambda: save_transcript(result, output_path / f"{base_name}.txt", format="txt")
                )
                await loop.run_in_executor(
                    None,
                    lambda: save_transcript(result, output_path / f"{base_name}.json", format="json")
                )
                
                logger.info(f"Saved transcription files to {output_path}")
            
            # Return SRT content for backward compatibility (matching local whisper)
            srt_content = transcript_to_srt(result)
            
            return [TextContent(
                type="text",
                text=srt_content
            )]
            
        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"File not found: {str(e)}"})
            )]
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Transcription failed: {str(e)}"})
            )]
    
    else:
        return [TextContent(
            type="text",
            text=json.dumps({"error": f"Unknown tool: {name}"})
        )]


async def main():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
