from contextlib import AsyncExitStack
from pathlib import Path
from typing import List, Optional

from agents import Agent, Runner, trace
from agents.mcp import MCPServerStdio

from video2md.prompt_loader import default_loader as prompts
from video2md.server.mcp_params import whisper_params, openai_transcribe_params, files_params


import logging

# Configure logging to capture tool calls
logging.basicConfig(level=logging.WARNING)

async def whisper_host(
    input_dir: str = "input",
    media_move_root: str = "output",
    model: str = "gpt-4o-mini",
    selected_files: Optional[List[str]] = None,
    transcribe_method: str = "local",
    enable_trace: bool = True,
) -> List[str]:
    """Transcribe media in a directory via MCP tools, then move files.

    Args:
        input_dir: Directory containing media files
        media_move_root: Directory to move processed media files
        model: LLM model for the agent
        selected_files: List of specific files to process (relative paths)
        transcribe_method: 'local' for faster-whisper or 'openai' for OpenAI API
        enable_trace: Whether to create trace for this agent (set False if parent already has trace)

    Returns a list of generated SRT paths.
    """
    system_prompt = prompts.load("whisper_host_instructions")

    # Configure MCP servers based on transcription method
    if transcribe_method == "openai":
        params = [
            {"param": openai_transcribe_params, "client_session_timeout_seconds": 600},
            {"param": files_params, "client_session_timeout_seconds": 60},
        ]
    else:  # default to local
        params = [
            {"param": whisper_params, "client_session_timeout_seconds": 600},
            {"param": files_params, "client_session_timeout_seconds": 60},
        ]

    async with AsyncExitStack() as stack:
        mcp_servers = [
            await stack.enter_async_context(
                MCPServerStdio(
                    params=param["param"],
                    client_session_timeout_seconds=param["client_session_timeout_seconds"],
                )
            )
            for param in params
        ]

        agent = Agent(
            name="WhisperHostAgent",
            model=model,
            instructions=system_prompt,
            mcp_servers=mcp_servers,
        )

        target = Path(input_dir)
        media_exts = {
            ".mp4",
            ".avi",
            ".mkv",
            ".mov",
            ".wmv",
            ".flv",
            ".webm",  # video
            ".mp3",
            ".wav",
            ".flac",
            ".aac",
            ".ogg",
            ".m4a",
            ".wma",  # audio
        }

        async def run_for_file(media_file: Path):
            media_path_str = str(media_file)
            base_name = media_file.stem
            # Unified per-media folder under ./output/<basename>
            dest_dir = f"{media_move_root}/{base_name}"
            srt_rel = f"{dest_dir}/{base_name}.srt"
            print(
                f"Configurations:\n"
                f"MEDIA_PATH: {media_path_str}\n"
                f"SRT_PATH: {srt_rel}\n"
                f"DEST_DIR: {dest_dir}\n"
            )

            message = prompts.render(
                "whisper_host_message",
                MEDIA_PATH=media_path_str,
                SRT_PATH=srt_rel,
                DEST_DIR=dest_dir,
                BASENAME=base_name,
            )

            # Only create trace if enable_trace is True
            if enable_trace:
                # Use base_name as group_id to group all agents for the same media file
                with trace(
                    workflow_name=f"Whisper Host Agent Runner: {media_file.name}",
                    group_id=base_name
                ):
                    return await Runner.run(agent, input=message)
            else:
                # Run without creating a new trace (parent trace will be used)
                return await Runner.run(agent, input=message)

        if not target.exists() or not target.is_dir():
            raise ValueError(f"Input must be a directory. Provided: {target}")

        # If a selection is provided, use only those files; otherwise, scan the directory
        if selected_files:
            resolved: List[Path] = []
            for f in selected_files:
                p = Path(f)
                if not p.is_absolute():
                    p = target / p
                if p.exists() and p.is_file() and p.suffix.lower() in media_exts:
                    resolved.append(p)
                else:
                    print(f"Skipping invalid or unsupported media: {p}")
            media_files = resolved
        else:
            media_files = [
                p
                for p in target.rglob("*")
                if p.is_file() and p.suffix.lower() in media_exts
            ]
        if not media_files:
            print(f"No media files found under {target}")
            return []

        srt_paths: List[str] = []
        for idx, mf in enumerate(sorted(media_files), 1):
            print(f"\n[{idx}/{len(media_files)}] Processing: {mf}")
            
            # Check for expected SRT before running (might already exist)
            srt_path = Path(media_move_root) / mf.stem / f"{mf.stem}.srt"
            
            try:
                result = await run_for_file(mf)
                print(f"Whisper Host Agent Result for {mf.name}: {result.final_output}")
            except Exception as e:
                error_msg = str(e)
                # Check if this is the known benign MCP tool error
                if "Invalid structured content for tool move_file" in error_msg:
                    logger.debug(f"Ignored benign MCP error for move_file: {error_msg}")
                    # Assume success if SRT exists (which we check below)
                elif "move_file" in error_msg and srt_path.exists():
                    print(f"Warning: MCP tool error occurred but SRT exists, continuing: {error_msg[:100]}")
                else:
                    print(f"Error processing {mf.name}: {e}")
                    # Check if SRT was still created despite the error
                    if not srt_path.exists():
                        continue  # Skip this file

            # Check for expected SRT in per-file output folder
            if srt_path.exists():
                srt_paths.append(str(srt_path))
            else:
                print(f"Warning: Expected SRT not found: {srt_path}")

        return srt_paths
