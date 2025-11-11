from contextlib import AsyncExitStack
from pathlib import Path
from typing import List, Dict, Any
import os

from agents import Agent, Runner, trace
from agents.mcp import MCPServerStdio

from video2md.prompt_loader import default_loader as prompts
from video2md.server.mcp_params import files_params, researcher_mcp_server_params


async def research_host(
    srts: List[str],
    model: str = "gpt-5-nano",
    prompt_variant: str = "github_project",
    user_notes: str | None = None,
) -> List[Dict[str, Any]]:
    """Run the Researcher agent across transcripts and return results per file.

    Args:
        srts: List of transcript file paths (.srt or .txt).
        model: LLM model name.
        prompt_variant: One of the researcher prompt variants inside
            prompts/researcher_instructions/ (e.g., github_project, general,
            tutorial, review_analysis). Defaults to github_project.
        user_notes: Optional extra context provided by the user to bias search
            (e.g., product spec hints, author commentary). Strongly prioritized
            over raw transcript tokens when conflicts arise.
    """
    # Load variant system instructions
    system_prompt = prompts.load(f"researcher_instructions/{prompt_variant}")
    results: List[Dict[str, Any]] = []

    # Per-tool client session timeout in seconds: if a tool call hangs (e.g., fetch to a blocked site),
    # the client will cut it off so the agent can try other sources. Keep Runner.run unbounded to
    # allow continued search after a single tool failure.
    try:
        tool_session_timeout_s = int(
            os.getenv("RESEARCH_TOOL_SESSION_TIMEOUT_SECONDS", "20"))
    except ValueError:
        tool_session_timeout_s = 20

    for srt in srts:
        srt_path = Path(srt)
        file_name = srt_path.stem
        # Prefer .txt transcript to reduce tokens; fallback to provided .srt
        txt_candidate = srt_path.with_suffix(".txt")
        transcript_path = txt_candidate if txt_candidate.exists() else srt_path
        async with AsyncExitStack() as stack:
            mcp_servers = [
                await stack.enter_async_context(
                    MCPServerStdio(
                        params=param,
                        client_session_timeout_seconds=tool_session_timeout_s,
                    )
                )
                for param in [files_params] + researcher_mcp_server_params
            ]

            agent = Agent(
                name="Researcher",
                model=model,
                instructions=system_prompt,
                mcp_servers=mcp_servers,
            )
            # Prepare structured input expected by the Researcher prompt
            message = prompts.render(
                "researcher_input",
                TRANSCRIPT_PATH=str(transcript_path),
                FILENAME_HINT=file_name,
                USER_NOTES=(user_notes or ""),
                PROMPT_VARIANT=prompt_variant,
            )

            with trace(f"Researcher Agent Runner: {file_name}"):
                res = await Runner.run(
                    agent,
                    input=message,
                    max_turns=20,
                )
            results.append({file_name: res.final_output})

    return results
