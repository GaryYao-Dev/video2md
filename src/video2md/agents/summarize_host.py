from pathlib import Path
from typing import List, Dict

from agents import Agent, Runner, trace

from video2md.prompt_loader import default_loader as prompts
from video2md.services.media_utils import read_transcript_text, find_moved_media


async def summarize_host(
    srts: List[str],
    researcher_results: List[Dict],
    model: str = "gpt-5-nano",
    enable_trace: bool = True,
) -> List[str]:
    """Create markdown summaries integrating transcript and research; embed original media.

    Args:
        srts: List of SRT file paths
        researcher_results: Research results from research_host
        model: LLM model name
        enable_trace: Whether to create trace for this agent (set False if parent already has trace)

    Returns a list of generated markdown file paths.
    """
    output_paths: List[str] = []
    root_output_dir = Path("output")
    root_output_dir.mkdir(parents=True, exist_ok=True)

    research_map: Dict[str, str] = {}
    for item in researcher_results:
        if isinstance(item, dict):
            for k, v in item.items():
                research_map[str(k)] = str(v)

    system_prompt = prompts.load("summarizer_instructions")

    for srt in srts:
        srt_path = Path(srt)
        file_name = srt_path.stem
        # With unified layout, media and transcripts live in ./output/<file_name>/
        per_file_dir = srt_path.parent if srt_path.parent.name == file_name else root_output_dir / file_name
        per_file_dir.mkdir(parents=True, exist_ok=True)
        media_file = find_moved_media(file_name, per_file_dir)
        research_text = research_map.get(file_name, "")
        # Prefer TXT transcript if available; otherwise, clean SRT to plain text
        transcript_text = read_transcript_text(srt_path)

        agent_input = prompts.render(
            "summarizer_input",
            FILENAME=file_name,
            TRANSCRIPT_TEXT=transcript_text,
            RESEARCH_TEXT=research_text,
        )

        agent = Agent(
            name="Summarizer",
            model=model,
            instructions=system_prompt,
        )

        # Only create trace if enable_trace is True
        if enable_trace:
            # Use file_name as group_id to group all agents for the same media file
            with trace(
                workflow_name=f"Summarizer Agent Runner: {file_name}",
                group_id=file_name
            ):
                res = await Runner.run(agent, input=agent_input)
                body_md = res.final_output or ""
        else:
            # Run without creating a new trace (parent trace will be used)
            res = await Runner.run(agent, input=agent_input)
            body_md = res.final_output or ""

        lines = [f"# {file_name}"]
        if media_file and media_file.exists():
            # Embed media from the same per-file folder
            rel_media = f"./{media_file.name}"
            lines += [
                "\n## Media",
                f"<video src=\"{rel_media}\" controls style=\"width:100%;max-width:100%;\"></video>",
                f"\n[Open media]({rel_media})\n",
            ]
        else:
            lines += [
                "\n## Media",
                f"Media file not found in ./{per_file_dir.relative_to(root_output_dir)} (summary generated from transcript).\n",
            ]

        lines.append(body_md.strip())

        out_path = per_file_dir / f"{file_name}.md"
        out_path.write_text("\n\n".join(lines) + "\n", encoding="utf-8")
        output_paths.append(str(out_path))

    return output_paths
