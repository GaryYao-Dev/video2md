from contextlib import AsyncExitStack
from pathlib import Path
from typing import List, Optional

from agents import Agent, Runner, trace
from agents.mcp import MCPServerStdio

from video2md.prompt_loader import default_loader as prompts
from video2md.server.mcp_params import whisper_params, files_params


async def whisper_host(
    input_dir: str = "input",
    media_move_root: str = "output",
    model: str = "gpt-4o-mini",
    selected_files: Optional[List[str]] = None,
) -> List[str]:
    """Transcribe media in a directory via MCP tools, then move files.

    Returns a list of generated SRT paths.
    """
    system_prompt = prompts.load("whisper_host_instructions")

    # Configure MCP servers
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

            with trace(f"Whisper Host Agent Runner: {media_file.name}"):
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
            result = await run_for_file(mf)
            print(
                f"Whisper Host Agent Result for {mf.name}: {result.final_output}")

            # Check for expected SRT in per-file output folder
            srt_path = Path(media_move_root) / mf.stem / f"{mf.stem}.srt"
            if srt_path.exists():
                srt_paths.append(str(srt_path))
            else:
                print(f"Warning: Expected SRT not found: {srt_path}")

        return srt_paths
