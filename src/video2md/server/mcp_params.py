import os
import sys
import shutil
from dotenv import load_dotenv

load_dotenv(override=True)


def _bin_available(cmd: str) -> bool:
    """Return True if an executable is available on PATH."""
    return shutil.which(cmd) is not None


# Whisper server parameters
# Prefer running with the current Python interpreter so we don't trigger
# on-demand installs via `uv run` for every invocation.
whisper_params = {
    "command": sys.executable,
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
