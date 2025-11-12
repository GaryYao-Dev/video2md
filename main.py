from video2md.agents.summarize_host import summarize_host
from video2md.agents.research_host import research_host
from video2md.agents.whisper_host import whisper_host
from video2md.utils.dependency_checker import DependencyChecker
from dotenv import load_dotenv
import sys
from pathlib import Path as _Path

# Ensure src/ is on sys.path when running from source tree
_SRC = _Path(__file__).resolve().parent / "src"
if _SRC.exists():
    sys.path.insert(0, str(_SRC))


# Load environment variables (e.g., WHISPER_API_URL)
load_dotenv(override=True)


async def run():
    # End-to-end: transcribe (or reuse), research, summarize
    srts = await whisper_host()
    # For quick testing, you can hardcode SRTs:
    # srts = ['whisper_output/windrecorder.srt']
    researcher_results = await research_host(srts)
    summaries = await summarize_host(srts, researcher_results)
    print("Generated summaries:\n" + "\n".join(summaries))


if __name__ == "__main__":
    import asyncio
    
    # Check dependencies before running
    DependencyChecker.validate_or_exit(require_ffmpeg=True, require_node=True)

    asyncio.run(run())
