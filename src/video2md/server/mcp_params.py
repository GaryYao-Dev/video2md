import os
import sys
import shutil
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)


def _bin_available(cmd: str) -> bool:
    """Return True if an executable is available on PATH."""
    return shutil.which(cmd) is not None


def _get_python_executable() -> str:
    """
    Get the correct Python executable for the current environment.
    Prefers uv virtual environment if available, otherwise uses sys.executable.
    """
    # Check if we're in a uv project (look for .venv in project root)
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent.parent  # Go up from src/video2md/server/mcp_params.py
    
    # Try Windows uv venv path
    uv_venv_win = project_root / ".venv" / "Scripts" / "python.exe"
    if uv_venv_win.exists():
        return str(uv_venv_win)
    
    # Try Unix uv venv path
    uv_venv_unix = project_root / ".venv" / "bin" / "python"
    if uv_venv_unix.exists():
        return str(uv_venv_unix)
    
    # Check VIRTUAL_ENV environment variable
    venv_path = os.getenv("VIRTUAL_ENV")
    if venv_path:
        venv_python_win = Path(venv_path) / "Scripts" / "python.exe"
        venv_python_unix = Path(venv_path) / "bin" / "python"
        if venv_python_win.exists():
            return str(venv_python_win)
        if venv_python_unix.exists():
            return str(venv_python_unix)
    
    # Fallback to current Python executable
    return sys.executable


# Whisper server parameters
# Prefer running with the current Python interpreter so we don't trigger
# on-demand installs via `uv run` for every invocation.
whisper_params = {
    "command": _get_python_executable(),
    "args": ["-m", "video2md.server.whisper_server"],
}

# Filesystem server parameters
# If a local/global install exists (recommended), use it; otherwise fall back to npx.
_fs_cmd_override = os.getenv(
    "MCP_FILESYSTEM_CMD") or os.getenv("FILESYSTEM_SERVER_CMD")
if _fs_cmd_override:
    files_params = {"command": _fs_cmd_override, "args": ["."]}
elif _bin_available("server-filesystem"):
    files_params = {"command": "server-filesystem", "args": ["."]}
elif _bin_available("mcp-server-filesystem"):
    # Some distros publish a different binary name
    files_params = {"command": "mcp-server-filesystem", "args": ["."]}
else:
    # Fall back to npx, but aggressively silence installer logs so stdout stays JSON-only.
    npm_silent_env = {
        "npm_config_loglevel": "silent",
        "npm_config_progress": "false",
        "npm_config_fund": "false",
        "npm_config_audit": "false",
        "NO_UPDATE_NOTIFIER": "1",
    }
    files_params = {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
        "env": npm_silent_env,
    }

# Researcher MCP server parameters (external MCPs)
brave_env = {"BRAVE_API_KEY": os.getenv("BRAVE_API_KEY")}
serper_env = {"SERPER_API_KEY": os.getenv("SERPER_API_KEY")}
researcher_mcp_server_params = []

# mcp-server-fetch: prefer preinstalled console script
if _bin_available("mcp-server-fetch"):
    researcher_mcp_server_params.append(
        {"command": "mcp-server-fetch", "args": []})
else:
    researcher_mcp_server_params.append(
        {"command": "uvx", "args": ["mcp-server-fetch"]})

# serper-mcp-server: prefer preinstalled console script
if _bin_available("serper-mcp-server"):
    researcher_mcp_server_params.append(
        {"command": "serper-mcp-server", "args": [], "env": serper_env})
else:
    researcher_mcp_server_params.append(
        {"command": "uvx", "args": ["serper-mcp-server"], "env": serper_env})
